from __future__ import annotations

from hybrid_ai_trading.execution.execution_engine_phase5_guard import place_order_phase5_with_guard


class _Engine:
    def __init__(self):
        self.is_paper = True  # keep paper so Block-G does not interfere
        self.risk_manager = None
        self.config = {"portfolio_halt": {"enabled": True, "max_drawdown": 0.05}}


def test_portfolio_halt_enabled_missing_metrics_blocks():
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
