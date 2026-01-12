import pytest

from hybrid_ai_trading.brokers.ib_client import IBClient, IBConfig

class DummyOrder: ...
class DummyTrade:
    def __init__(self):
        self.order = DummyOrder()
    def isActive(self):
        return True

class DummyContract:
    def __init__(self, symbol="NVDA"):
        self.symbol = symbol

class DummyPos:
    def __init__(self, sym="NVDA", qty=1):
        self.contract = DummyContract(sym)
        self.position = qty

class DummyIB:
    def __init__(self):
        self.cancelled = 0
        self.orders = []
    def openTrades(self):
        return [DummyTrade(), DummyTrade()]
    def cancelOrder(self, order):
        self.cancelled += 1
    def positions(self):
        return [DummyPos("NVDA", 2), DummyPos("NVDA", -1)]
    def placeOrder(self, *args):
        # should not be called directly in this test (we monkeypatch chokepoint)
        self.orders.append(args)

def test_ibclient_cancel_and_close_use_chokepoint(monkeypatch):
    c = IBClient(IBConfig(client_id=9999))
    c.ib = DummyIB()  # inject dummy

    calls = []
    def fake_choke(ib, contract, order, ctx=None, meta=None):
        calls.append({"ib": ib, "sym": getattr(contract, "symbol", ""), "meta": dict(meta or {})})
        return {"ok": True}

    monkeypatch.setattr("hybrid_ai_trading.brokers.ib_client.ib_place_order_chokepoint", fake_choke)

    r1 = c.cancel_all_open_orders()
    assert r1["status"] == "ok"
    assert r1["cancelled"] == 2
    assert c.ib.cancelled == 2

    r2 = c.close_all_positions(meta={"symbol": "NVDA"})
    assert r2["status"] == "ok"
    assert r2["closed"] == 2  # two nonzero positions

    # Ensure allow_risk_action is forced true
    assert all(x["meta"].get("allow_risk_action") is True for x in calls)
