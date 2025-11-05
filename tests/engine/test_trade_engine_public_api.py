import math

import pytest


# offline broker stub
class _StubBroker:
    def connect(self):
        return True

    def disconnect(self):
        pass

    def server_time(self):
        return "2025-10-11 00:00:00"

    def place_order(
        self, symbol, side, qty, order_type="MARKET", limit_price=None, meta=None
    ):
        oid = 1
        return oid, {
            "status": "Filled" if order_type == "MARKET" else "Submitted",
            "filled": float(qty or 0),
            "avgPrice": float(limit_price or 0.0),
            "meta": meta or {},
        }

    def open_orders(self):
        return []

    def positions(self):
        return [{"symbol": "AAPL", "position": 1.0}]


@pytest.fixture()
def engine(monkeypatch):
    # ensure both factory and order_manager symbols resolve to our stub
    from hybrid_ai_trading import order_manager as om_mod
    from hybrid_ai_trading.brokers import factory as broker_factory

    monkeypatch.setattr(
        broker_factory, "make_broker", lambda: _StubBroker(), raising=True
    )
    monkeypatch.setattr(om_mod, "make_broker", lambda: _StubBroker(), raising=True)

    import hybrid_ai_trading.trade_engine as te

    # constructor signature you reported: TradeEngine(config, portfolio=None, brokers=None)
    eng = te.TradeEngine(config={})
    return eng


def test_public_methods_basic(engine):
    # adaptive_fraction
    af = engine.adaptive_fraction()
    assert isinstance(af, float) or isinstance(af, int)

    # alert
    msg = engine.alert("hello")
    assert isinstance(msg, dict) and msg

    # getters
    eq = engine.get_equity()
    assert isinstance(eq, (int, float))
    hist = engine.get_history()
    assert isinstance(hist, list)
    pos = engine.get_positions()
    assert isinstance(pos, dict)


def test_process_signal_paths(engine):
    # BUY path
    r1 = engine.process_signal("AAPL", "BUY", price=100.0, size=1)
    assert isinstance(r1, dict)

    # SELL path
    r2 = engine.process_signal("AAPL", "SELL", price=101.0, size=1)
    assert isinstance(r2, dict)

    # HOLD/unknown path Ã¢â‚¬â€ exercise default/else branch
    r3 = engine.process_signal("AAPL", "HOLD", price=102.0, size=0)
    assert isinstance(r3, dict)


def test_record_and_reset(engine):
    # positive + negative pnl to cross both sides
    engine.record_trade_outcome(+10.0)
    engine.record_trade_outcome(-5.0)

    out = engine.reset_day()
    assert isinstance(out, dict)
