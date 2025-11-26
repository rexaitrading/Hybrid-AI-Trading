"""
Phase-5 execution guard helpers.

This module exposes place_order_phase5_with_guard(engine, **kwargs),
which wraps the existing place_order_phase5 with Phase-5 risk checks.
"""

from __future__ import annotations

from typing import Any, Dict

from hybrid_ai_trading.execution.execution_engine import place_order_phase5
from hybrid_ai_trading.risk.risk_phase5_engine_guard import guard_phase5_trade
from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision


def place_order_phase5_with_guard(engine: Any, **kwargs: Any) -> Dict[str, Any]:
    """
    Guarded version of place_order_phase5 for Phase-5 runners.

    Expected kwargs include at least:
        symbol, side, qty, price, maybe regime, day_id

    If engine.risk_manager is missing, this behaves like the original
    place_order_phase5 (no Phase-5 risk applied).
    """
    rm = getattr(engine, "risk_manager", None)
    if rm is None:
        # No risk manager available; fall back to original behavior.
        return place_order_phase5(engine=engine, **kwargs)

    symbol = str(kwargs.get("symbol", kwargs.get("sym", "UNKNOWN")))
    side = str(kwargs.get("side", "")).upper()
    qty = kwargs.get("qty", kwargs.get("size", 0.0))
    price = float(kwargs.get("price", 0.0) or 0.0)
    regime = str(kwargs.get("regime", "SPY_ORB_LIVE"))
    day_id = (
        kwargs.get("day_id")
        or kwargs.get("session_date")
        or str(kwargs.get("ts", ""))[:10]
        or "UNKNOWN"
    )

    try:
        qty_f = float(qty)
    except (TypeError, ValueError):
        qty_f = 0.0

    trade: Dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "qty": qty_f,
        "price": price,
        "regime": regime,
        "day_id": day_id,
    }

    decision: Phase5RiskDecision = guard_phase5_trade(rm, trade)

    if not decision.allowed:
        # Blocked by Phase-5 risk; return a synthetic result.
        return {
            "status": "blocked_phase5",
            "symbol": symbol,
            "side": side,
            "qty": qty_f,
            "reason": decision.reason,
            "phase5_details": decision.details,
        }

    # Phase-5 risk allowed. Decide how to call the underlying engine.

    # Case 1: real engine with place_order -> call full place_order_phase5
    if hasattr(engine, "place_order"):
        # Ensure entry_ts exists for the underlying engine
        if "entry_ts" not in kwargs:
            day_id_for_ts = (
                kwargs.get("day_id")
                or kwargs.get("session_date")
                or str(kwargs.get("ts", ""))[:10]
                or "1970-01-01"
            )
            kwargs["entry_ts"] = f"{day_id_for_ts}T00:00:00Z"

        # Remove Phase-5-only helper key before calling the underlying engine
        kwargs.pop("day_id", None)

        return place_order_phase5(engine=engine, **kwargs)

    # Case 2: Dummy/test engine with no place_order - return a safe stub dict
    return {
        "status": "ok_phase5_stub",
        "symbol": symbol,
        "side": side,
        "qty": qty_f,
        "price": price,
        "regime": regime,
        "phase5_reason": decision.reason,
        "phase5_details": decision.details,
    }