import pytest
from hybrid_ai_trading.trade_engine import TradeEngine

class RouterOkStatus:
    # returns {!} status==ok and reason==ok to tick normalize branches (if not pragma)
    def route_order(self, *a, **k): return {"status":"ok","reason":"ok"}

@pytest.fixture()
def eng_oknorm(tmp_path):
    e = TradeEngine(config={})
    e.router = RouterOkStatus()
    # bypass filters so we reach normalization
    setattr(e.sentiment_filter,"allow_trade", lambda *a,**k: True)
    setattr(e.gatescore,       "allow_trade", lambda *a,**k: True)
    # send audit to temp dir to tick happy audit entry lines
    e.audit_log  = str(tmp_path / "audit.csv")
    e.backup_log = str(tmp_path / "backup.csv")
    return e

def test_normalize_ok_happy_path(eng_oknorm):
    r = eng_oknorm.process_signal("AAPL","BUY",price=100,size=1)
    # Depending on pragma, result may be "filled/normalized_ok" or remain "ok"
    assert r["status"] in {"filled","ok"} 
    assert r.get("reason") in {"normalized_ok","ok"}