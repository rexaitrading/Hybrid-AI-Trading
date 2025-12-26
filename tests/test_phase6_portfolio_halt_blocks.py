from hybrid_ai_trading.execution.execution_engine_phase5_guard import place_order_phase5_with_guard


class DummyPortfolio:
    def report(self):
        return {"var95": 1.0, "cvar95": 1.0, "drawdown": 0.5}


class DummyEngine:
    def __init__(self):
        self.is_paper = True
        self.config = {"portfolio_halt": {"enabled": True, "max_var95": 0.2}}
        self.portfolio_tracker = DummyPortfolio()
        self.risk_manager = None
        self.engine_called = False

    def place_order(self, **kwargs):
        self.engine_called = True
        return {"status": "ok"}


def test_portfolio_halt_enabled_blocks_before_order_send():
    eng = DummyEngine()
    out = place_order_phase5_with_guard(
        eng, symbol="AAPL", side="BUY", qty=1, price=100.0, regime="TEST", day_id="TEST"
    )
    assert out["status"] == "blocked"
    assert "portfolio_halt:" in out["reason"]
    assert eng.engine_called is False