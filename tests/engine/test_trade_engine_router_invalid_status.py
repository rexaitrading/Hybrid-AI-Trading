import pytest

from hybrid_ai_trading.trade_engine import TradeEngine


class RouterWeird:
    def route_order(self, *a, **k):
        return {"status": "nope"}  # not in allowed set


@pytest.fixture()
def eng():
    e = TradeEngine(config={})
    e.router = RouterWeird()
    return e


def test_router_invalid_status(eng, monkeypatch):
    # allow filters/perf so router normalization is reached
    monkeypatch.setattr(
        eng.sentiment_filter, "allow_trade", lambda *a, **k: True, raising=True
    )
    monkeypatch.setattr(
        eng.gatescore, "allow_trade", lambda *a, **k: True, raising=True
    )
    r = eng.process_signal(
        "AAPL", "BUY", price=100, size=1
    )  # algo=None â†’ router branch
    assert r == {"status": "rejected", "reason": "invalid_status"}
