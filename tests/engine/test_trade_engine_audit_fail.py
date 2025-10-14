import pytest
from hybrid_ai_trading.trade_engine import TradeEngine

class RouterOK:
    def route_order(self, *a, **k): return {"status":"filled","reason":"ok"}

@pytest.fixture()
def eng_ok():
    e = TradeEngine(config={})
    e.router = RouterOK()
    # Let filters pass so we reach normalization + audit
    setattr(e.sentiment_filter, "allow_trade", lambda *a, **k: True)
    setattr(e.gatescore,        "allow_trade", lambda *a, **k: True)
    return e

def test_audit_write_failure_is_logged(monkeypatch, eng_ok, caplog):
    # Make audit raise so we hit logger.error lines (351–352)
    monkeypatch.setattr(eng_ok, "_write_audit", lambda row: (_ for _ in ()).throw(RuntimeError("disk")), raising=True)
    r = eng_ok.process_signal("AAPL","BUY",price=100,size=1)
    assert r["status"] in {"filled","rejected","blocked","ok","error","pending","ignored"}
    assert any("Audit log capture failed" in msg for msg in [rec.message for rec in caplog.records])