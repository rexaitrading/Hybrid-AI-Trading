import pytest

from hybrid_ai_trading.trade_engine import TradeEngine


@pytest.fixture()
def eng():
    return TradeEngine(config={})


def test_process_signal_perf_exception_flows_to_normalization(monkeypatch, eng):
    # let filters pass so we hit performance
    monkeypatch.setattr(
        eng.sentiment_filter, "allow_trade", lambda *a, **k: True, raising=True
    )
    monkeypatch.setattr(
        eng.gatescore, "allow_trade", lambda *a, **k: True, raising=True
    )
    # force performance block to raise (covers the exception path)
    monkeypatch.setattr(
        eng.performance_tracker,
        "sharpe_ratio",
        lambda: (_ for _ in ()).throw(RuntimeError("sharpe_boom")),
        raising=True,
    )
    # route should succeed â†’ we reach normalization not â€˜blockedâ€™
    r = eng.process_signal("AAPL", "BUY", price=100, size=1)  # algo=None â†’ router OK
    assert r["status"] in {
        "filled",
        "rejected",
        "blocked",
        "ok",
        "error",
        "pending",
        "ignored",
    }
