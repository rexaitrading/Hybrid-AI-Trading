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
        # This test engine represents PAPER execution unless explicitly overridden
        self.is_paper = True


def test_place_order_phase5_with_guard_calls_underlying_and_allows_in_paper():
    """
    Institutional rule: PAPER must never be blocked by Block-G readiness.
    This test verifies the guarded path returns the underlying stub result.
    """
    engine = DummyEngine()
    result = place_order_phase5_with_guard(
        engine,
        symbol="SPY",
        side="BUY",
        qty=1.0,
        price=500.0,
        regime="SPY_ORB_PAPER",
        day_id="2025-11-10",
    )
    assert isinstance(result, dict)
    assert result.get("status") == "ok_stub_engine"


def test_blockg_contract_failure_blocks_nvda_live(monkeypatch):
    """
    If contract gate fails for NVDA live intent,
    place_order_phase5_with_guard must surface a RuntimeError
    and must NOT call place_order_phase5.
    """
    import hybrid_ai_trading.execution.execution_engine_phase5_guard as guard_mod

    class DummyDecision:
        def __init__(self) -> None:
            self.allowed = True
            self.reason = "ok"
            self.details = {}

    class DummyEngine2:
        def __init__(self) -> None:
            self.is_paper = False
            self.risk_manager = object()

    # 1) Risk guard always allows the trade (focus this test on Block-G contract)
    def fake_guard_phase5_trade(rm, trade):
        return DummyDecision()

    # 2) Force contract gate failure deterministically
    def fake_enforce_blockg_if_live(ctx, symbol: str, *, is_live=None):
        class D:
            ok = False
            reasons = ["Block-G NVDA not ready"]
        return D()

    # 3) If place_order_phase5 is ever reached, fail loudly
    def fail_place_order_phase5(*args, **kwargs):
        raise AssertionError("place_order_phase5 should NOT be called when Block-G is not ready")

    monkeypatch.setattr(guard_mod, "guard_phase5_trade", fake_guard_phase5_trade)
    monkeypatch.setattr(guard_mod, "enforce_blockg_if_live", fake_enforce_blockg_if_live)
    monkeypatch.setattr(guard_mod, "place_order_phase5", fail_place_order_phase5)

    engine = DummyEngine2()

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