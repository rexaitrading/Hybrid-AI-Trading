from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision
from hybrid_ai_trading.blockg_contract import require_blockg_ready
from hybrid_ai_trading.runtime.run_context import RunContext


def guard_phase5_trade(rm: Any, trade: Dict[str, Any]) -> Phase5RiskDecision:
    """
    Thin shim so tests and callers have a single place to hook Phase-5 guards.
    """

    # --- BLOCK-G: fail-closed readiness enforcement ---
    symbol = str(trade.get("symbol", "") or "").strip().upper()
    d = require_blockg_ready(symbol)
    if not d.ready:
        raise RuntimeError(
            f"BLOCK-G NOT READY: symbol={d.symbol} as_of_date={d.as_of_date} reason={d.reason}"
        )

    if rm is None:
        raise RuntimeError("RiskManager is required for Phase-5 guard")

    decision = rm.check_trade_phase5(trade)
    if not isinstance(decision, Phase5RiskDecision):
        raise TypeError("check_trade_phase5 must return Phase5RiskDecision")

    return decision


def ensure_symbol_blockg_ready(symbol: str, engine: object | None = None, ctx: RunContext | None = None) -> None:
    """
    Enforce Block-G contract for LIVE orders.

    - Paper engines bypass.
    - Live engines MUST pass Block-G.
    - Delegates to require_blockg_ready(), which reads blockg_status_stub.json.
    """

    if engine is not None and getattr(engine, "is_paper", False):
        return

    if ctx is None and engine is not None:
        ctx = getattr(engine, "run_context", None)

    if ctx is not None:
        # Canonical live safety gate (RunContext is the single authority)
        ctx.require_live_safe()
        return

    d = require_blockg_ready(symbol)
    if not d.ready:
        raise RuntimeError(
            f"BLOCK-G NOT READY: symbol={d.symbol} as_of_date={d.as_of_date} reason={d.reason}"
        )


def place_order_phase5(
    engine: Any,
    symbol: str,
    side: str,
    qty: float,
    price: float,
    regime: str,
    day_id: str | None = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Underlying Phase-5 order placement hook (stub for tests).
    """
    return {
        "status": "ok_stub_engine",
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "price": price,
        "regime": regime,
        "day_id": day_id,
        "extra": kwargs,
    }


def place_order_phase5_with_guard(
    engine: Any,
    symbol: str,
    side: str,
    qty: float,
    price: float,
    regime: str,
    day_id: str | None = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Phase-5 guarded order entry used by tests and live runners.
    """

    trade = {
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "price": price,
        "regime": regime,
        "day_id": day_id,
        **kwargs,
    }

    # 1) Block-G enforcement for LIVE orders
    if "LIVE" in (regime or "").upper():
        ensure_symbol_blockg_ready(symbol, engine=engine)

    # 2) Phase-5 RiskManager guard
    rm = getattr(engine, "risk_manager", None)
    if rm is not None:
        decision = guard_phase5_trade(rm, trade)
        if not decision.allowed:
            return {
                "status": "blocked_by_phase5_risk",
                "reason": decision.reason,
                "decision": asdict(decision),
            }

    # 3) Place order
    return place_order_phase5(
        engine=engine,
        symbol=symbol,
        side=side,
        qty=qty,
        price=price,
        regime=regime,
        day_id=day_id,
        **kwargs,
    )