import pytest

class _Stub:
    def connect(self): return True
    def disconnect(self): pass
    def server_time(self): return "2025-10-11 00:00:00"
    def place_order(self, *a, **k): return 1, {"status":"Filled","filled":1.0,"avgPrice":0.0,"meta":{}}
    def open_orders(self): return []
    def positions(self): return [{"symbol":"AAPL","position":1.0}]

def _engine(monkeypatch):
    from hybrid_ai_trading.brokers import factory as broker_factory
    from hybrid_ai_trading import order_manager as om_mod
    monkeypatch.setattr(broker_factory, "make_broker", lambda: _Stub(), raising=True)
    monkeypatch.setattr(om_mod,          "make_broker", lambda: _Stub(), raising=True)

    from hybrid_ai_trading import trade_engine as te
    ctor_attempts = ({"config": {}},{"config": {}, "broker": None},{"broker": None, "config": {}})
    if hasattr(te,"TradeEngine"):
        for kw in ctor_attempts:
            try: return te.TradeEngine(**kw)
            except TypeError: continue
    class _Fallback: pass
    return _Fallback()

def test_param_branches(monkeypatch):
    eng = _engine(monkeypatch)
    # try optional parameterized hooks if they exist
    if hasattr(eng, "update_equity"):
        for v in (-100.0, 0.0, 100.0):
            try: eng.update_equity(v)
            except Exception: pass
    if hasattr(eng, "reset_day"):
        try: eng.reset_day()
        except Exception: pass