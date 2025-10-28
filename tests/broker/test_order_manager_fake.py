import os

from hybrid_ai_trading.order_manager import OrderManager


def test_order_manager_fake(monkeypatch):
    monkeypatch.setenv("BROKER_BACKEND", "fake")
    om = OrderManager()
    om.start()
    res = om.buy_market("AAPL", 2)
    assert res["orderId"] == 1
    assert res["filled"] >= 0
    pos = om.positions()
    assert any(p["symbol"] == "AAPL" for p in pos)
    om.stop()
