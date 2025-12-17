from __future__ import annotations


from hybrid_ai_trading.execution.blockg_runtime import enforce_blockg_if_live
from hybrid_ai_trading.runtime.run_context import RunContext, RunMode
from hybrid_ai_trading.risk.risk_phase5_ev_bands import get_ev_and_band
from dataclasses import asdict
from typing import Any, Dict

from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision
from hybrid_ai_trading.blockg_contract import require_blockg_ready
from hybrid_ai_trading.runtime.run_context import RunContext


def guard_phase5_trade(rm: Any, trade: Dict[str, Any]) -> Phase5RiskDecision:
    """
    Thin shim so tests and callers have a single place to hook Phase-5 guards.

    IMPORTANT: Block-G is enforced in the LIVE execution path (RunContext / engine layer),
    not inside this RiskManager shim. This keeps unit tests deterministic.
    """
    if rm is None:
        raise RuntimeError("RiskManager is required for Phase-5 guard")

    decision = rm.check_trade_phase5(trade)
    if not isinstance(decision, Phase5RiskDecision):
        raise TypeError("check_trade_phase5 must return Phase5RiskDecision")

    return decision


def ensure_symbol_blockg_ready(symbol: str, engine: object | None = None, ctx: RunContext | None = None, **_ignore: Any) -> None:
    """
    Enforce Block-G contract for LIVE orders (fail-closed).
    - Paper engines bypass (artifact generation must never be blocked).
    - Canonical enforcement for real live engines is RunContext.require_live_safe().
    """
    # Paper/replay engines must never be blocked by readiness flags.
    if engine is not None and getattr(engine, "is_paper", False):
        return

    d = require_blockg_ready(symbol)
    if not d.ready:
        raise RuntimeError(
            f"BLOCK-G NOT READY: symbol={d.symbol} as_of_date={d.as_of_date} reason={d.reason}"
        )

def _require_engine_live_gate(engine: object, symbol: str) -> None:
    """
    Canonical Phase-5 live gate (fail-closed).

    Enforces:
      - engine.run_context exists
      - run_context.require_live_safe(...)
      - Block-G symbol readiness
    """
    ctx = getattr(engine, "run_context", None)
    if ctx is None:
        raise RuntimeError("[PHASE5] Missing RunContext on engine (fail-closed).")

    # Prefer symbol-aware gate when supported
    try:
        ctx.require_live_safe(symbol=symbol)
    except TypeError:
        ctx.require_live_safe()

    # Block-G gate (contract truth)
    ensure_symbol_blockg_ready(symbol, engine=engine, ctx=ctx)



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
    ev_mu, ev_band_abs = (None, None)
    try:
        ev_mu, ev_band_abs = get_ev_and_band(str(regime))
    except Exception:
        ev_mu, ev_band_abs = (None, None)

    return {
        "status": "ok_stub_engine",
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "price": price,
        "regime": regime,
        "day_id": day_id,
        "extra": kwargs,

        # Phase-5 EV surface (deterministic from ev-band table; may be None)
        "ev_mu": ev_mu,
        "ev_band_abs": ev_band_abs,
        "phase5_result": {
            "ev_mu": ev_mu,
            "ev_band_abs": ev_band_abs,
            "source": "ev_band_table",
        },
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
    }    # 1) Unified RunContext + Block-G enforcement (single authority, fail-closed)
    ctx = getattr(engine, "run_context", None) or RunContext.from_env()

    # Define "LIVE" consistently: either ctx.mode==LIVE OR regime contains LIVE
    is_live = (ctx.mode == RunMode.LIVE) or ("LIVE" in (regime or "").upper())
    if is_live:
        # Canonical gate: requires Block-G contract truth
        dec = enforce_blockg_if_live(ctx, symbol)
        if not dec.ok:
            raise RuntimeError(f"BLOCKG_DENY:{symbol}:" + ",".join(dec.reasons))

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

