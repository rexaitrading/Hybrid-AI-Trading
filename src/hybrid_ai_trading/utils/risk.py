from __future__ import annotations

from hybrid_ai_trading.broker.ib_safe import ib_place_order_chokepoint
import os
from ib_insync import IB, MarketOrder

from hybrid_ai_trading.execution.blockg_enforce import require_blockg_ready_for_live


def _blockg_guard_live_risk_flatten(symbol: str) -> None:
    """
    Fail-closed Block-G guard for any direct ib.placeOrder() usage in utils.risk flatten path.

    Policy:
    - Only enforce for NVDA/SPY/QQQ (extend later).
    - Enforce only when live intent (HAT_IS_PAPER=0).
    - If env cannot be read, fail-closed (treat as live).
    """
    sym_u = str(symbol or "").upper()
    if sym_u not in ("NVDA", "SPY", "QQQ"):
        return
    try:
        env_flag = os.environ.get("HAT_IS_PAPER", "1").strip()
        is_live = (env_flag == "0")
    except Exception:
        is_live = True
    if is_live:
        require_blockg_ready_for_live(sym_u)


def intraday_risk_checks(
    ib: IB, max_gross=200_000, max_pos_per_name=5_000, max_draw=-1500
):
    # basic guards; extend with PnL tracking as needed
    positions = list(ib.positions())
    # gross exposure approximation (shares only)
    gross = sum(abs(int(p.position)) for p in positions)
    if gross > max_gross:
        for t in ib.openTrades():
            ib.cancelOrder(t.order)
        _flatten(ib, positions)
    for p in positions:
        if abs(p.position) > max_pos_per_name:
            _flatten_one(ib, p)


def _flatten(ib: IB, positions):
    for p in positions:
        _flatten_one(ib, p)


def _flatten_one(ib: IB, p):
    side = "SELL" if p.position > 0 else "BUY"
    # Block-G: do not allow live bypass on flatten
    _blockg_guard_live_risk_flatten(getattr(p.contract, "symbol", ""))
    ib_place_order_chokepoint(ib, p.contract, MarketOrder(side, abs(int(p.position))))
