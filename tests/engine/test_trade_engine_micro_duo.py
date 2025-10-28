import pytest
from hybrid_ai_trading.trade_engine import TradeEngine

@pytest.fixture()
def eng():
    return TradeEngine(config={})

def test_reset_day_portfolio_then_risk_error(monkeypatch, eng):
    # 1) portfolio reset throws -> portfolio_reset_failed:*
    monkeypatch.setattr(eng.portfolio, "reset_day", lambda: (_ for _ in ()).throw(ValueError("pboom")), raising=True)
    r1 = eng.reset_day()
    assert r1["status"] == "error" and r1["reason"].startswith("portfolio_reset_failed:")
    # 2) risk reset throws -> risk_reset_failed:*
    monkeypatch.setattr(eng.portfolio, "reset_day", lambda: {"status":"ok"}, raising=True)
    monkeypatch.setattr(eng.risk_manager, "reset_day", lambda: (_ for _ in ()).throw(RuntimeError("rboom")), raising=True)
    r2 = eng.reset_day()
    assert r2["status"] == "error" and r2["reason"].startswith("risk_reset_failed:")
