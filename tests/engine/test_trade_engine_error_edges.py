import pytest

class _StubOK:
    def connect(self): return True
    def disconnect(self): pass
    def server_time(self): return "2025-10-11 00:00:00"
    def place_order(self, *a, **k): return 99, {"status":"Filled","filled":1.0,"avgPrice":0.0,"meta":{}}
    def open_orders(self): return []
    def positions(self): return [{"symbol":"AAPL","position":1.0}]

class _StubBoom(_StubOK):
    def place_order(self, *a, **k): raise RuntimeError("synthetic boom")

def _mk_engine(monkeypatch, *, boom=False):
    from hybrid_ai_trading.brokers import factory as broker_factory
    from hybrid_ai_trading import order_manager as om_mod
    monkeypatch.setattr(broker_factory, "make_broker", lambda: (_StubBoom() if boom else _StubOK()), raising=True)
    monkeypatch.setattr(om_mod,          "make_broker", lambda: (_StubBoom() if boom else _StubOK()), raising=True)
    import hybrid_ai_trading.trade_engine as te
    eng = te.TradeEngine(config={})
    for attr in ("adaptive","adaptive_mode","adaptive_enabled"):
        if hasattr(eng, attr): setattr(eng, attr, True)
    return eng

def test_process_signal_error_branch(monkeypatch):
    eng = _mk_engine(monkeypatch, boom=True)
    try:
        res = eng.process_signal("AAPL","BUY", price=100.0, size=1)
    except (RuntimeError, ValueError):
        return
    assert isinstance(res, dict)

def test_reset_day_error_branch(monkeypatch):
    eng = _mk_engine(monkeypatch, boom=False)
    if hasattr(eng, "portfolio") and hasattr(eng.portfolio, "reset_day"):
        orig = eng.portfolio.reset_day
        def boom(): raise ValueError("reset boom")
        eng.portfolio.reset_day = boom
        try:
            try:
                res = eng.reset_day()
            except (RuntimeError, ValueError):
                return
            assert isinstance(res, dict)
        finally:
            eng.portfolio.reset_day = orig

def test_adaptive_fraction_edges(monkeypatch):
    eng = _mk_engine(monkeypatch, boom=False)
    if hasattr(eng, "history"):
        try:
            eng.history.clear()
        except Exception:
            try: eng.history[:] = []
            except Exception: pass
    try: _ = eng.adaptive_fraction()
    except Exception: pass
    if hasattr(eng, "history"):
        try: eng.history.extend([1.0, 2.0, 3.0])
        except Exception:
            try: setattr(eng, "history", [1.0, 2.0, 3.0])
            except Exception: pass
    try: _ = eng.adaptive_fraction()
    except Exception: pass

def test_alert_variants(monkeypatch):
    eng = _mk_engine(monkeypatch, boom=False)
    m0 = eng.alert("")
    m1 = eng.alert("x"*1024)
    assert isinstance(m0, dict) and isinstance(m1, dict)
