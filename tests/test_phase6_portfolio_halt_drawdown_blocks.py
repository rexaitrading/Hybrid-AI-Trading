from __future__ import annotations

from hybrid_ai_trading.execution.execution_engine_phase5_guard import place_order_phase5_with_guard


class _PT:
    def report(self):
        return {"var95": 0.0, "cvar95": 0.0, "drawdown": 0.50}


class _Engine:
    def __init__(self):
        self.is_paper = True
        self.risk_manager = None
        self.portfolio_tracker = _PT()
        self.config = {"portfolio_halt": {"enabled": True, "max_drawdown": 0.05}}


def test_portfolio_halt_drawdown_blocks():
    engine = _Engine()
    out = place_order_phase5_with_guard(
        engine=engine,
        symbol="NVDA",
        side="BUY",
        qty=1,
        price=1.0,
        regime="TEST",
    )
    assert isinstance(out, dict)
    assert out.get("status") == "blocked"
    assert "portfolio_halt" in str(out.get("reason", ""))
