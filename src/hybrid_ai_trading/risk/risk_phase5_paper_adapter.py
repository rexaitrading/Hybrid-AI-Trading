"""
Phase-5 paper/live RiskManager adapter (stub version).

Goal:
- Provide a check_trade(trade: Dict[str, Any]) -> Dict[str, Any] interface
  compatible with Phase-5 runners.
- For now, this is a clear stub that always allows.
- Later, we can wire this through to the real risk engine backend
  (daily loss caps, MDD, cooldowns, etc.) without changing runner code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Phase5TradeContext:
    symbol: str
    side: str
    qty: float
    price: float
    regime: str
    ts: Optional[str]


class Phase5RiskAdapter:
    """
    Phase-5 paper/live risk adapter (stub).

    This version does NOT talk to the real risk engine yet.
    It always allows trades, and clearly marks itself as a stub
    so JSONL / logs never confuse this with real risk wiring.
    """

    def __init__(self, backend: Any | None = None) -> None:
        # Keep the field so we can wire a backend later without
        # changing the interface.
        self._backend: Any | None = backend
        self._backend_source: str = "none" if backend is None else "external"

    def _build_context(self, trade: Dict[str, Any]) -> Phase5TradeContext:
        symbol = str(trade.get("symbol", "UNKNOWN"))
        side_raw = str(trade.get("side", "long")).upper()
        side = "LONG" if "SHORT" not in side_raw else "SHORT"

        qty = float(trade.get("qty", 0.0) or trade.get("size", 0.0) or 0.0)
        price = float(trade.get("price", 0.0) or trade.get("entry_price", 0.0) or 0.0)
        regime = str(trade.get("regime", "UNKNOWN"))
        ts = trade.get("ts") or trade.get("entry_ts")

        return Phase5TradeContext(
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            regime=regime,
            ts=ts,
        )

    def check_trade(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase-5 compatible check_trade interface.

        STUB BEHAVIOR:
        - Always returns allowed=True.
        - Puts a very explicit stub reason so there is no confusion in JSONL.
        """
        _ctx = self._build_context(trade)

        return {
            "allowed": True,
            "reason": (
                "phase5_risk_adapter_stub "
                "(no real risk engine wired yet)"
            ),
        }