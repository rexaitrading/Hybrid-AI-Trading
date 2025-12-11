from types import SimpleNamespace

import pytest

from hybrid_ai_trading.execution.execution_engine_phase5_guard import (
    place_order_phase5_with_guard,
)
from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision


class DummyEngine:
    def __init__(self) -> None:
        # Minimal RiskManager-like object with a stub check_trade_phase5
        self.risk_manager = SimpleNamespace(
            check_trade_phase5=lambda trade: Phase5RiskDecision(
                allowed=True,
                reason="phase5_risk_ok",
                details={"test": True},
            )
        )


def test_place_order_phase5_with_guard_calls_underlying_and_allows():
    engine = DummyEngine()
    result = place_order_phase5_with_guard(
        engine,
        symbol="SPY",
        side="BUY",
        qty=1.0,
        price=500.0,
        regime="SPY_ORB_LIVE",
        day_id="2025-11-10",
    )

    # We don't assert exact shape of the underlying result, just that
    # the function returns a dict and did not synthesize a blocked result.
    assert isinstance(result, dict)
    assert result.get("status") == "ok_stub_engine"


def test_blockg_contract_failure_blocks_nvda_live(monkeypatch):
    """
    If ensure_symbol_blockg_ready raises for NVDA live,
    place_order_phase5_with_guard must surface that RuntimeError
    and must NOT call place_order_phase5.
    """
    import hybrid_ai_trading.execution.execution_engine_phase5_guard as guard_mod

    class DummyDecision:
        def __init__(self) -> None:
            self.allowed = True
            self.reason = "ok"
            self.details = {}

    class DummyEngine:
        def __init__(self) -> None:
            # Risk manager just needs to be non-None so guard_phase5_trade is invoked
            self.risk_manager = object()

    # 1) Risk guard always allows the trade (focus this test on Block-G contract)
    def fake_guard_phase5_trade(rm, trade):
        return DummyDecision()

    # 2) Block-G helper fails hard for NVDA
    def fake_ensure_symbol_blockg_ready(symbol: str):
        raise RuntimeError("Block-G NVDA not ready")

    # 3) If place_order_phase5 is ever reached, we want the test to fail loudly
    def fail_place_order_phase5(*args, **kwargs):
        raise AssertionError("place_order_phase5 should NOT be called when Block-G is not ready")

    monkeypatch.setattr(guard_mod, "guard_phase5_trade", fake_guard_phase5_trade)
    monkeypatch.setattr(guard_mod, "ensure_symbol_blockg_ready", fake_ensure_symbol_blockg_ready)
    monkeypatch.setattr(guard_mod, "place_order_phase5", fail_place_order_phase5)

    engine = DummyEngine()

    with pytest.raises(RuntimeError) as excinfo:
        guard_mod.place_order_phase5_with_guard(
            engine,
            symbol="NVDA",
            side="BUY",
            qty=1.0,
            price=100.0,
            regime="NVDA_BPLUS_LIVE",
        )

    assert "Block-G NVDA not ready" in str(excinfo.value)
