from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict
from hybrid_ai_trading.runtime.run_context import RunContext

from hybrid_ai_trading.portfolio.halts import require_portfolio_halt_ok
from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision
from hybrid_ai_trading.execution.blockg_contract import (
    ensure_symbol_blockg_ready as contract_ensure_symbol_blockg_ready,
)
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


def ensure_symbol_blockg_ready(symbol: str) -> None:
    """
    Block-G contract enforcement for live NVDA / SPY / QQQ.

    In production, this delegates to hybrid_ai_trading.execution.blockg_contract.ensure_symbol_blockg_ready,
    which reads logs/blockg_status_stub.json written by Build-BlockGStatusStub.ps1.

    Tests may monkeypatch this function to simulate Block-G failures without touching
    the underlying contract helper.
    """
    contract_ensure_symbol_blockg_ready(symbol, allow_paper=True, is_paper=False, ctx=None)


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
    # 0) Hard Block-G enforcement for LIVE orders (fail-closed, contract-only)
    try:
        is_paper = bool(getattr(engine, "is_paper", True))
    except Exception:
        is_paper = True
    sym_u = str(symbol).upper()
    is_live_regime = ("_LIVE" in str(regime).upper()) or ("LIVE" in str(regime).upper())
    if (sym_u in ("NVDA","SPY","QQQ")) and ((not is_paper) or is_live_regime):
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
