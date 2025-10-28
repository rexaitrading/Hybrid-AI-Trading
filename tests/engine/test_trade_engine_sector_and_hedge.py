import pytest
from hybrid_ai_trading.trade_engine import TradeEngine

def _router_ok():
    class R:
        def route_order(self, *a, **k):
            return {"status":"filled","reason":"ok"}
    return R()

@pytest.fixture()
def eng_sector():
    # tiny cap so exposure/equity >= cap trips branch
    cfg = {"risk":{"intraday_sector_exposure": 0.0001, "equity": 100000.0}}
    e = TradeEngine(config=cfg)
    e.router = _router_ok()
    # let filters pass so guardrails are exercised deterministically
    setattr(e.sentiment_filter, "allow_trade", lambda *a, **k: True)
    setattr(e.gatescore,        "allow_trade", lambda *a, **k: True)
    return e

def test_sector_exposure_breach_blocks(eng_sector, monkeypatch):
    # forge large tech exposure so exposure/equity >= cap
    positions = {
        "AAPL": {"size": 1000, "avg_price": 1000},  # 1,000,000 exposure
        "MSFT": {"size":  100, "avg_price": 1000},
    }
    monkeypatch.setattr(eng_sector.portfolio, "get_positions", lambda: positions, raising=True)
    r = eng_sector.process_signal("AAPL","BUY",price=100,size=1)
    assert r["status"] == "blocked" and r["reason"] == "sector_exposure"

def test_hedge_rule_blocks(monkeypatch):
    # fresh engine with hedge rule for AAPL
    cfg = {"risk":{"hedge_rules":{"equities_vol_spike":["AAPL"]}, "equity": 100000.0}}
    e = TradeEngine(config=cfg)
    e.router = _router_ok()
    setattr(e.sentiment_filter,"allow_trade", lambda *a,**k: True)
    setattr(e.gatescore,       "allow_trade", lambda *a,**k: True)
    r = e.process_signal("AAPL","SELL",price=100,size=1)
    assert r["status"] == "blocked" and r["reason"] == "hedge_rule"
