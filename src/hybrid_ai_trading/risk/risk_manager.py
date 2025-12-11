from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Dict

from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision


@dataclass
class RiskManager:
    """
    Minimal RiskManager stub for Phase-5 tests.

    - Holds a simple config object (SimpleNamespace is fine)
    - Tracks daily PnL per day_id
    - Tracks positions as a dict[symbol] -> object with qty and avg_price

    The real implementation can grow around this interface, but these
    attributes and check_trade_phase5 semantics should remain stable.
    """

    config: Any = None
    daily_pnl: Dict[str, float] = field(default_factory=dict)
    positions: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.config is None:
            # Default config with no hard daily loss cap
            self.config = SimpleNamespace(phase5_daily_loss_cap=None)

    # ---- Helpers -----------------------------------------------------

    def _get_daily_pnl(self, day_id: str) -> float:
        try:
            return float(self.daily_pnl.get(day_id, 0.0))
        except (TypeError, ValueError):
            return 0.0

    def _get_daily_loss_cap(self) -> float | None:
        cap = getattr(self.config, "phase5_daily_loss_cap", None)
        if cap is None:
            return None
        try:
            return float(cap)
        except (TypeError, ValueError):
            return None

    def _get_position(self, symbol: str) -> Any:
        return self.positions.get(symbol)

    # ---- Phase-5 combined gates -------------------------------------

    def check_trade_phase5(self, trade: Dict[str, Any]) -> Phase5RiskDecision:
        """
        Phase-5 combined gates used by tests:

        1) Daily loss cap:
           - If phase5_daily_loss_cap is set, and current daily_pnl[day_id]
             is BELOW or equal to the cap (i.e. more negative),
             and the trade increases directional exposure,
             block with reason 'daily_loss_cap_block'.

        2) No averaging down:
           - If long and trying to buy more below avg_price, block with
             'no_averaging_down_long_block'.
           - (Short-side rule can be added later.)

        Otherwise:
           - Allow with reason containing 'daily_loss'.
        """
        symbol = str(trade.get("symbol", "")).upper()
        side = str(trade.get("side", "")).upper()
        qty = float(trade.get("qty", 0.0) or 0.0)
        price = float(trade.get("price", 0.0) or 0.0)
        day_id = str(trade.get("day_id", "") or "")

        daily_pnl = self._get_daily_pnl(day_id)
        cap = self._get_daily_loss_cap()
        pos = self._get_position(symbol)
        pos_qty = float(getattr(pos, "qty", 0.0) or 0.0)
        avg_price = float(getattr(pos, "avg_price", price) or price)

        # 1) Daily loss cap gate
        if cap is not None:
            # "Below cap" means more negative than the cap (e.g. -600 < -500)
            loss_breached = daily_pnl <= cap

            # Exposure increases if we trade in the same direction as the current position
            exposure_increases = False
            if side == "BUY" and pos_qty > 0:
                exposure_increases = qty > 0
            elif side == "SELL" and pos_qty < 0:
                exposure_increases = qty > 0

            if loss_breached and exposure_increases:
                return Phase5RiskDecision(
                    allowed=False,
                    reason="daily_loss_cap_block",
                    details={
                        "day_id": day_id,
                        "symbol": symbol,
                        "daily_pnl": daily_pnl,
                        "cap": cap,
                        "pos_qty": pos_qty,
                        "side": side,
                        "qty": qty,
                    },
                )

        # 2) No averaging down gate (long-side only for now)
        if side == "BUY" and pos_qty > 0:
            # Long 1 @100, trying to buy more at 95 -> averaging down long
            if price < avg_price:
                return Phase5RiskDecision(
                    allowed=False,
                    reason="no_averaging_down_long_block",
                    details={
                        "symbol": symbol,
                        "day_id": day_id,
                        "pos_qty": pos_qty,
                        "avg_price": avg_price,
                        "new_price": price,
                    },
                )

        # 3) Default: allow, with reason mentioning daily_loss
        return Phase5RiskDecision(
            allowed=True,
            reason=f"daily_loss_ok(current={daily_pnl})",
            details={
                "symbol": symbol,
                "day_id": day_id,
                "daily_pnl": daily_pnl,
                "cap": cap,
                "pos_qty": pos_qty,
            },
        )