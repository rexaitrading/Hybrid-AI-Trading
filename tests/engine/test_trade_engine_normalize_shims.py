import pytest

from hybrid_ai_trading.trade_engine import TradeEngine


class RouterPendingOk:
    def route_order(self, *a, **k):
        return {"status": "pending", "reason": "ok"}


@pytest.fixture()
def e_norm():
    e = TradeEngine(config={})
    e.router = RouterPendingOk()
    setattr(e.sentiment_filter, "allow_trade", lambda *a, **k: True)
    setattr(e.gatescore, "allow_trade", lambda *a, **k: True)
    return e


def test_normalize_reason_only(e_norm):
    r = e_norm.process_signal("AAPL", "BUY", price=100, size=1)
    assert r["status"] in {"pending", "filled"} and r.get("reason") in {"normalized_ok", "ok"}
