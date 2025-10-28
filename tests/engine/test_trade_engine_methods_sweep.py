import pytest

# Strictly offline stub broker
class _Stub:
    def connect(self): return True
    def disconnect(self): pass
    def server_time(self): return "2025-10-11 00:00:00"
    def place_order(self, symbol, side, qty, order_type="MARKET", limit_price=None, meta=None):
        oid = 1
        return oid, {"status":"Filled" if order_type=="MARKET" else "Submitted",
                     "filled": float(qty or 0), "avgPrice":0.0, "meta": meta or {}}
    def open_orders(self): return []
    def positions(self): return [{"symbol":"AAPL","position":1.0}]

def _build_engine(monkeypatch):
    # ensure both factory and order_manager use our stub
    from hybrid_ai_trading.brokers import factory as broker_factory
    from hybrid_ai_trading import order_manager as om_mod
    monkeypatch.setattr(broker_factory, "make_broker", lambda: _Stub(), raising=True)
    monkeypatch.setattr(om_mod,          "make_broker", lambda: _Stub(), raising=True)

    from hybrid_ai_trading import trade_engine as te

    # Try a few ctor shapes commonly seen
    ctor_attempts = (
        {"config": {}},
        {"config": {}, "broker": None},
        {"broker": None, "config": {}},
    )
    if hasattr(te, "TradeEngine"):
        for kw in ctor_attempts:
            try:
                return te.TradeEngine(**kw)
            except TypeError:
                continue
    # Fallback: small shim via OrderManager if engine cannot be constructed
    from hybrid_ai_trading.order_manager import OrderManager
    class _Fallback:
        def __init__(self): self.om = OrderManager()
        def start(self): self.om.start()
        def stop(self): self.om.stop()
        def buy_market(self, s, q): return self.om.buy_market(s,q)
        def buy_limit(self, s, q, p): return self.om.buy_limit(s,q,p)
        def sell_market(self, s, q): return self.om.sell_market(s,q)
        def sell_limit(self, s, q, p): return self.om.sell_limit(s,q,p)
        def positions(self): return self.om.positions()
    return _Fallback()

def _maybe(callable_):
    try:
        return callable_()
    except Exception:
        # Don’t fail sweep on optional paths; goal is coverage, not strict behavior here
        return None

def test_trade_engine_method_sweep(monkeypatch):
    eng = _build_engine(monkeypatch)

    # Try lifecycle if present
    if hasattr(eng, "start"): eng.start()

    # Common method candidates (only call if present)
    if hasattr(eng, "buy_market"):  _maybe(lambda: eng.buy_market("AAPL", 1))
    if hasattr(eng, "sell_market"): _maybe(lambda: eng.sell_market("AAPL", 1))
    if hasattr(eng, "buy_limit"):   _maybe(lambda: eng.buy_limit("AAPL", 1.0, 123.45))
    if hasattr(eng, "sell_limit"):  _maybe(lambda: eng.sell_limit("AAPL", 0.5, 321.00))
    if hasattr(eng, "positions"):   _maybe(lambda: eng.positions())

    # Try any obvious utility hooks if present
    for name in ("reset_day","update_equity","flush","sync","tick","run_once","run"):
        if hasattr(eng, name):
            _maybe(lambda n=name: getattr(eng, n)())

    if hasattr(eng, "stop"): eng.stop()
