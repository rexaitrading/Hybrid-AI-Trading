import pytest
from hybrid_ai_trading.trade_engine import TradeEngine

@pytest.fixture()
def eng(): return TradeEngine(config={})

def test_reset_ok_then_error(monkeypatch, eng):
    # Force OK
    monkeypatch.setattr(eng.portfolio,"reset_day",lambda: {"status":"ok"}, raising=True)
    monkeypatch.setattr(eng.risk_manager,"reset_day",lambda: {"status":"ok"}, raising=True)
    ok1 = eng.reset_day();  assert ok1["status"] == "ok"
    # Force risk to fail
    monkeypatch.setattr(eng.risk_manager,"reset_day",lambda: (_ for _ in ()).throw(RuntimeError("boom")), raising=True)
    bad = eng.reset_day()
    assert bad["status"] == "error" and bad["reason"].startswith("risk_reset_failed:")
