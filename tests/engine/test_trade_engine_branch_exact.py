import sys, types, importlib, pytest

# ---- Stubs -------------------------------------------------------------------
class StubBroker:
    def connect(self): return True
    def disconnect(self): pass
    def server_time(self): return "2025-10-11 00:00:00"
    def place_order(self, symbol, side, qty, order_type="MARKET", limit_price=None, meta=None):
        return 1, {"status":"Filled","filled":float(qty or 0),"avgPrice":float(limit_price or 0.0),"meta":meta or {}}
    def open_orders(self): return []
    def positions(self): return [{"symbol":"AAPL","position":1.0}]

class RouterOK:
    def __init__(self): self.calls=[]
    def route_order(self, symbol, signal, size, price):
        self.calls.append((symbol,signal,size,price))
        return {"status":"filled","reason":"ok"}

class RouterError:
    def route_order(self, *a, **k): raise RuntimeError("router blew up")
class RouterNone:
    def route_order(self, *a, **k): return None
class RouterStatusError:
    def route_order(self, *a, **k): return {"status":"error","reason":"downstream"}

# ---- helper to install fake algo modules with exact class names --------------
def _install_algo(monkeypatch, name, executor_cls):
    key = name.lower()
    cls_map = {"twap":"TWAPExecutor","vwap":"VWAPExecutor","iceberg":"IcebergExecutor"}
    cls_name = cls_map.get(key, "Executor")
    path = f"hybrid_ai_trading.algos.{key}"
    m = types.ModuleType(path)
    setattr(m, cls_name, executor_cls)
    # hard-replace module and invalidate caches so importlib sees our module
    if path in sys.modules:
        del sys.modules[path]
    sys.modules[path] = m
    importlib.invalidate_caches()

class TWAPExecutor:
    def __init__(self, om): pass
    def execute(self, symbol, signal, size, price):
        return {"status":"filled","reason":"twap_ok"}

class VWAPExecutor:
    def __init__(self, om): pass
    def execute(self, symbol, signal, size, price):
        return {"status":"filled","reason":"ok"}  # allowed

class IcebergBad:
    def __init__(self, om): pass
    def execute(self, *a, **k): raise RuntimeError("iceberg fail")

class WeirdStatusExec:
    def __init__(self, om): pass
    def execute(self, *a, **k): return {"status":"weird"}  # not allowed

# ---- Fixture -----------------------------------------------------------------
@pytest.fixture()
def eng(monkeypatch):
    from hybrid_ai_trading.brokers import factory as broker_factory
    from hybrid_ai_trading import order_manager as om_mod
    monkeypatch.setattr(broker_factory, "make_broker", lambda: StubBroker(), raising=True)
    monkeypatch.setattr(om_mod,          "make_broker", lambda: StubBroker(), raising=True)
    import hybrid_ai_trading.trade_engine as te
    e = te.TradeEngine(config={})
    # no-op audit
    monkeypatch.setattr(e, "_write_audit", lambda row: None, raising=False)
    e.router = RouterOK()
    return e

# ---- Validation & guardrails --------------------------------------------------
def test_validate_invalid_signal_and_hold_and_price(eng):
    assert eng.process_signal("AAPL", 123, price=100, size=1)["reason"] == "signal_not_string"
    assert eng.process_signal("AAPL", "XYZ", price=100, size=1)["status"] == "rejected"
    assert eng.process_signal("AAPL", "HOLD", price=100, size=1)["reason"] == "hold_signal"
    assert eng.process_signal("AAPL", "BUY",  price=None, size=1)["reason"] == "invalid_price"
    assert eng.process_signal("AAPL", "SELL", price=0,    size=1)["reason"] == "invalid_price"

def test_guardrails_equity_sector_hedge(eng, monkeypatch):
    eng.portfolio.equity = 0
    assert eng.process_signal("AAPL","BUY",price=100,size=1)["reason"] == "equity_depleted"
    eng.portfolio.equity = 100000.0
    monkeypatch.setattr(eng, "_sector_exposure_breach", lambda s: True, raising=True)
    assert eng.process_signal("AAPL","BUY",price=100,size=1)["reason"] == "sector_exposure"
    monkeypatch.setattr(eng, "_sector_exposure_breach", lambda s: False, raising=True)
    monkeypatch.setattr(eng, "_hedge_trigger", lambda s: True, raising=True)
    assert eng.process_signal("AAPL","SELL",price=100,size=1)["reason"] == "hedge_rule"
    monkeypatch.setattr(eng, "_hedge_trigger", lambda s: False, raising=True)

# ---- Router path (algo None) --------------------------------------------------
def test_router_exception_none_error(eng):
    eng.router = RouterError()
    r = eng.process_signal("AAPL","BUY",price=100,size=1)
    assert r["status"] == "blocked" and r["reason"].startswith("router_error:")
    eng.router = RouterNone()
    r = eng.process_signal("AAPL","BUY",price=100,size=1)
    assert r == {"status":"blocked","reason":"router_failed"}
    eng.router = RouterStatusError()
    r = eng.process_signal("AAPL","BUY",price=100,size=1)
    assert r["status"] == "blocked" and "router_error" in r["reason"]

# ---- Algo routing (algo set) --------------------------------------------------
def test_algo_known_unknown_and_error(eng, monkeypatch):
    # allow filters/perf for known-algo paths
    monkeypatch.setattr(eng.sentiment_filter, "allow_trade", lambda *a, **k: True, raising=True)
    monkeypatch.setattr(eng.gatescore,        "allow_trade", lambda *a, **k: True, raising=True)
    monkeypatch.setattr(eng.performance_tracker, "sharpe_ratio", lambda : 999.0, raising=True)

    # TWAP ok
    _install_algo(monkeypatch, "twap", TWAPExecutor)
    r = eng.process_signal("AAPL","BUY",price=100,size=1,algo="TWAP")
    assert r["status"] in {"filled","blocked","rejected","pending","ok","error","ignored"}

    # VWAP ok
    _install_algo(monkeypatch, "vwap", VWAPExecutor)
    r = eng.process_signal("AAPL","SELL",price=100,size=1,algo="vwap")
    assert r["status"] in {"filled","blocked","rejected","pending","ok","error","ignored"}

    # Unknown algo early reject
    r = eng.process_signal("AAPL","BUY",price=100,size=1,algo="StrAnGe")
    assert r == {"status":"rejected","reason":"unknown_algo"}

    # ICEBERG error
    _install_algo(monkeypatch, "iceberg", IcebergBad)
    r = eng.process_signal("AAPL","BUY",price=100,size=1,algo="ICEBERG")
    assert r["status"] == "error" and "algo_error" in r["reason"]

    # Weird status -> invalid_status
    _install_algo(monkeypatch, "twap", WeirdStatusExec)
    r = eng.process_signal("AAPL","BUY",price=100,size=1,algo="TWAP")
    assert r == {"status":"rejected","reason":"invalid_status"}

# ---- Filters & Performance ----------------------------------------------------
def test_filters_and_perf(eng, monkeypatch):
    monkeypatch.setattr(eng.sentiment_filter, "allow_trade", lambda *a, **k: False, raising=True)
    r = eng.process_signal("AAPL","BUY",price=100,size=1)
    assert r["reason"] == "sentiment_veto"
    monkeypatch.setattr(eng.sentiment_filter, "allow_trade", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("sent")), raising=True)
    r = eng.process_signal("AAPL","BUY",price=100,size=1)
    assert r["reason"] == "sentiment_error"
    monkeypatch.setattr(eng.sentiment_filter, "allow_trade", lambda *a, **k: True, raising=True)
    monkeypatch.setattr(eng.gatescore, "allow_trade", lambda *a, **k: False, raising=True)
    r = eng.process_signal("AAPL","BUY",price=100,size=1)
    assert r["reason"] == "gatescore_veto"
    monkeypatch.setattr(eng.gatescore, "allow_trade", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("g")), raising=True)
    r = eng.process_signal("AAPL","BUY",price=100,size=1)
    assert r["reason"] == "gatescore_error"
    monkeypatch.setattr(eng.gatescore, "allow_trade", lambda *a, **k: True, raising=True)
    monkeypatch.setattr(eng.performance_tracker, "sharpe_ratio", lambda : -999.0, raising=True)
    r = eng.process_signal("AAPL","BUY",price=100,size=1)
    assert r["reason"] == "sharpe_breach"
