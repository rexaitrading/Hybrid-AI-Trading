import importlib
import sys
import types

import pytest

from hybrid_ai_trading.trade_engine import TradeEngine


# publish a real module with the exact CamelCase class the engine imports
def _install(monkeypatch, name, executor_cls):
    key = name.lower()
    cls = {
        "twap": "TWAPExecutor",
        "vwap": "VWAPExecutor",
        "iceberg": "IcebergExecutor",
    }[key]
    path = f"hybrid_ai_trading.algos.{key}"
    m = types.ModuleType(path)
    setattr(m, cls, executor_cls)
    if path in sys.modules:
        del sys.modules[path]
    sys.modules[path] = m
    importlib.invalidate_caches()


class WeirdExec:  # returns status not in allowed set Ã¢â€ â€™ invalid_status
    def __init__(self, om):
        pass

    def execute(self, *a, **k):
        return {"status": "weird"}


@pytest.fixture()
def eng():
    return TradeEngine(config={})


def test_algo_invalid_status(monkeypatch, eng):
    # allow filters/perf so we reach normalization
    monkeypatch.setattr(
        eng.sentiment_filter, "allow_trade", lambda *a, **k: True, raising=True
    )
    monkeypatch.setattr(
        eng.gatescore, "allow_trade", lambda *a, **k: True, raising=True
    )
    _install(monkeypatch, "twap", WeirdExec)
    r = eng.process_signal("AAPL", "BUY", price=100, size=1, algo="TWAP")
    assert r == {"status": "rejected", "reason": "invalid_status"}
