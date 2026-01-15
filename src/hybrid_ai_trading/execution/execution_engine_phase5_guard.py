from __future__ import annotations


import os
from dataclasses import asdict
from typing import Any, Dict
from hybrid_ai_trading.runtime.run_context import RunContext
from hybrid_ai_trading.execution.blockg_ps_checker import require_blockg_ready_via_powershell

from hybrid_ai_trading.portfolio.halts import require_portfolio_halt_ok
from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision

def guard_phase5_trade(rm: Any, trade: Dict[str, Any]) -> Phase5RiskDecision:
    """
    Thin shim so tests and callers have a single place to hook Phase-5 guards.
    """
    if rm is None:
        raise RuntimeError("RiskManager is required for Phase-5 guard")
    decision = rm.check_trade_phase5(trade)
    if not isinstance(decision, Phase5RiskDecision):
        raise TypeError("check_trade_phase5 must return Phase5RiskDecision")
    return decision


def ensure_symbol_blockg_ready(symbol: str, ctx: RunContext | None = None) -> None:
    # PAPER/PAPERLIVE must NOT consult Block-G; LIVE-only enforcement (fail-closed).
    mode = (os.getenv("HAT_MODE", "PAPER") or "PAPER").strip().upper()
    is_paper = (os.getenv("HAT_IS_PAPER", "1") or "1").strip().lower() in ("1","true","yes")
    if mode != "LIVE" or is_paper:
        return



    """
    Backward-compatible shim.
    Single Python entrypoint is hybrid_ai_trading.execution.blockg_enforce.require_blockg_ready_for_live.
    Tests may monkeypatch this function to simulate failures.
    """
    mk = None
    try:
        mk = str(getattr(ctx, "market", "")).upper().strip() if ctx is not None else None
    except Exception:
        mk = None
    require_blockg_ready_via_powershell(str(symbol).upper().strip(), market=mk, build=False)


def _infer_is_paper(engine: Any, regime: str, ctx: RunContext | None) -> bool:
    """
    Institutional: determine paper/live mode with defense-in-depth.
    Priority:
      1) ctx (if provided and has is_paper)
      2) engine.is_paper attribute
      3) env HAT_IS_PAPER (0 => live)
      4) regime contains LIVE marker
      default: paper
    """
    try:
        if ctx is not None and hasattr(ctx, "is_paper"):
            return bool(getattr(ctx, "is_paper"))
    except Exception:
        pass
    try:
        if hasattr(engine, "is_paper"):
            return bool(getattr(engine, "is_paper"))
    except Exception:
        pass
    try:
        v = str(__import__("os").environ.get("HAT_IS_PAPER", "")).strip()
        if v != "":
            return (v != "0")
    except Exception:
        pass
    try:
        r = str(regime).upper()
        if ("_LIVE" in r) or ("LIVE" in r):
            return False
    except Exception:
        pass
    return True

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
    Underlying Phase-5 order placement hook.

    For tests we keep this as a simple stub that returns a dict.
    Real implementation can call into the full execution engine / IB wrapper.
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
    Phase-5 wrapper used by tests:

    1) For NVDA, enforce Block-G readiness via ensure_symbol_blockg_ready.
    2) If engine.risk_manager exists, run guard_phase5_trade:
       - if blocked -> synthesize a blocked result.
       - if allowed -> call place_order_phase5.

    Tests only assert:
      - function returns a dict when risk is allowed
      - Block-G failure for NVDA raises and place_order_phase5 is never called.
    """
    # 0) Hard Block-G enforcement for LIVE orders (PowerShell is semantic owner; fail-closed)
    sym_u = str(symbol).upper()

    ctx = None
    try:
        # Prefer explicit ctx passed via kwargs (unified RunContext semantics)
        if "ctx" in kwargs and kwargs.get("ctx") is not None:
            ctx = kwargs.get("ctx")
        else:
            ctx = getattr(engine, "ctx", None)
    except Exception:
        ctx = None

    is_paper = _infer_is_paper(engine=engine, regime=str(regime), ctx=ctx)

    # Institutional: enforce via PowerShell checker for NVDA/SPY/QQQ in LIVE mode.
    # (Paper allowed to proceed; closed-day exit=10 remains LIVE-disallowed.)
    if (sym_u in ("NVDA", "SPY", "QQQ")) and (not is_paper):
        # Unified Block-G gate (JSON + PS checker; fail-closed)
        # Backward-compatible: tests may monkeypatch ensure_symbol_blockg_ready(symbol) only.
        try:
            ensure_symbol_blockg_ready(sym_u, ctx=ctx)
        except TypeError:
            ensure_symbol_blockg_ready(sym_u)

    trade = {
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "price": price,
        "regime": regime,
        "day_id": day_id,
        **kwargs,
    }

    # 1.5) Phase-6 Portfolio Halt (optional; fail-closed when enabled)
    try:
        cfg = {}
        try:
            if hasattr(engine, "config") and isinstance(getattr(engine, "config"), dict):
                cfg = dict(engine.config.get("portfolio_halt", {}))
        except Exception:
            cfg = {}
        # default behavior: disabled unless explicitly enabled
        if bool(cfg.get("enabled", False)):
            metrics = {}
            try:
                if hasattr(engine, "portfolio_tracker"):
                    metrics = dict(engine.portfolio_tracker.report())
            except Exception:
                metrics = {}
            require_portfolio_halt_ok(metrics=metrics, cfg=cfg)
    except Exception as e:
        # Fail-closed: block trade if portfolio halt trips or metrics unavailable when enabled
        return {"status": "blocked", "reason": f"portfolio_halt:{e}"}

    # 2) RiskManager Phase-5 guard
    rm = getattr(engine, "risk_manager", None)
    if rm is not None:
        decision = guard_phase5_trade(rm, trade)
        if not decision.allowed:
            # Synthesized blocked result
            return {
                "status": "blocked_by_phase5_risk",
                "reason": decision.reason,
                "decision": asdict(decision),
            }

    # 3) Call underlying order function
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
