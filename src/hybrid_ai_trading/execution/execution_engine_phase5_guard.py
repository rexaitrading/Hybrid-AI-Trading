from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

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
    contract_ensure_symbol_blockg_ready(symbol)


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
    trade = {
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "price": price,
        "regime": regime,
        "day_id": day_id,
        **kwargs,
    }

    # 1) Block-G for NVDA (tests monkeypatch ensure_symbol_blockg_ready)
    if symbol.upper() == "NVDA":
        ensure_symbol_blockg_ready(symbol.upper())

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

def ensure_nvda_live_allowed_by_blockg() -> None:
    """
    Hard Block-G contract enforcement for NVDA live orders.

    This MUST be called before any live NVDA order is sent.

    Contract:
    - Uses logs/blockg_status_stub.json built by Run-BlockGReadiness.ps1
    - Enforces:
        - status.is_today
        - phase23_health_ok_today
        - ev_hard_daily_ok_today
        - gatescore_fresh_today
        - nvda_blockg_ready
    """
    try:
        assert_symbol_ready_for_live("NVDA")
    except BlockGNotReadyError as exc:
        # Raise a clear error so guard tests and execution engine can intercept.
        raise RuntimeError(f"NVDA live order blocked by Block-G contract: {exc}") from exc