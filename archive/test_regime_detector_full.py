"""
Unit Tests: RegimeDetector (Hybrid AI Quant Pro v16.35 – 100% Coverage, Branch-Safe)
-----------------------------------------------------------------------------------
"""

from datetime import datetime, timedelta

import pandas as pd
import pytest

from hybrid_ai_trading.risk.regime_detector import RegimeDetector

# --- Dummy DB stubs --------------------------------------------------


class DummyPrice:
    def __init__(self, close, symbol="AAPL", timestamp=None):
        self.close = close
        self.symbol = symbol
        self.timestamp = timestamp or datetime.utcnow()


class DummySession:
    def __init__(self, prices):
        self._prices = prices

    def query(self, _):
        return self

    def filter(self, *_, **__):
        return self

    def order_by(self, *_, **__):
        return self

    def all(self):
        return self._prices

    def close(self):
        return None


class BrokenSession:
    def query(self, *_):
        raise Exception("DB fail")

    def close(self):
        return None


# --- Fixture ---------------------------------------------------------


@pytest.fixture
def detector():
    return RegimeDetector(
        lookback_days=30,
        bull_threshold=0.01,
        bear_threshold=-0.01,
        crisis_volatility=0.03,
        min_samples=3,
        neutral_tolerance=1e-4,
    )


# --- Init / Config ---------------------------------------------------


def test_init_defaults_from_config(monkeypatch):
    monkeypatch.setattr(
        "hybrid_ai_trading.risk.regime_detector.CONFIG",
        {
            "regime": {
                "enabled": False,
                "method": "simple",
                "lookback_days": 10,
                "bull_threshold": 0.1,
                "bear_threshold": -0.1,
                "crisis_volatility": 0.5,
                "min_samples": 5,
            }
        },
    )
    d = RegimeDetector(enabled=None, method=None, min_samples=None)
    assert d.enabled is False
    assert d.method == "simple"
    assert d.min_samples == 5


# --- Detect branches -------------------------------------------------


def test_detect_disabled(detector):
    detector.enabled = False
    result = detector.detect("AAPL", prices=[100, 101])
    assert result == "neutral"


def test_detect_no_data(detector):
    result = detector.detect("AAPL", prices=[])
    assert result == "neutral"


def test_detect_insufficient_data(detector):
    detector.min_samples = 10
    result = detector.detect("AAPL", prices=[100, 101])
    assert result == "neutral"


def test_detect_empty_returns(monkeypatch, detector):
    monkeypatch.setattr(
        pd.Series, "pct_change", lambda self: pd.Series([], dtype="float64")
    )
    result = detector.detect("AAPL", prices=[100, 101, 102])
    assert result == "sideways"


def test_detect_exception_in_stats(monkeypatch, detector):
    monkeypatch.setattr(
        pd.Series, "mean", lambda *_: (_ for _ in ()).throw(Exception("boom"))
    )
    result = detector.detect("AAPL", prices=[100, 101, 102])
    assert result == "neutral"


def test_detect_bull(monkeypatch, detector):
    monkeypatch.setattr(pd.Series, "mean", lambda *_: 0.05)
    monkeypatch.setattr(pd.Series, "std", lambda *_: 0.01)

    class DummySeries(pd.Series):
        def sum(self, *_, **__):
            return 999.0

    monkeypatch.setattr(pd.Series, "abs", lambda self: DummySeries([1.0, 1.0]))
    result = detector.detect("AAPL", prices=[100, 110, 120])
    assert result == "bull"


def test_detect_bear(monkeypatch, detector):
    monkeypatch.setattr(pd.Series, "mean", lambda *_: -0.05)
    monkeypatch.setattr(pd.Series, "std", lambda *_: 0.01)

    class DummySeries(pd.Series):
        def sum(self, *_, **__):
            return 999.0

    monkeypatch.setattr(pd.Series, "abs", lambda self: DummySeries([1.0, 1.0]))
    result = detector.detect("AAPL", prices=[100, 90, 80])
    assert result == "bear"


def test_detect_crisis(monkeypatch, detector):
    monkeypatch.setattr(pd.Series, "mean", lambda *_: 0.0)
    monkeypatch.setattr(pd.Series, "std", lambda *_: 0.5)

    class DummySeries(pd.Series):
        def sum(self, *_, **__):
            return 999.0

    monkeypatch.setattr(pd.Series, "abs", lambda self: DummySeries([1.0, 1.0]))
    result = detector.detect("AAPL", prices=[100, 200, 50])
    assert result == "crisis"


def test_detect_transition(monkeypatch, detector):
    monkeypatch.setattr(pd.Series, "mean", lambda *_: 0.005)
    monkeypatch.setattr(pd.Series, "std", lambda *_: 0.02)

    class DummySeries(pd.Series):
        def sum(self, *_, **__):
            return 999.0

    monkeypatch.setattr(pd.Series, "abs", lambda self: DummySeries([1.0, 1.0]))
    result = detector.detect("AAPL", prices=[100, 101, 100.5])
    assert result == "transition"


def test_detect_sideways(monkeypatch, detector):
    monkeypatch.setattr(pd.Series, "mean", lambda *_: 0.0)
    monkeypatch.setattr(pd.Series, "std", lambda *_: 0.0)

    class DummySeries(pd.Series):
        def sum(self, *_, **__):
            return 0.0

    monkeypatch.setattr(pd.Series, "abs", lambda self: DummySeries([0.0, 0.0]))
    result = detector.detect("AAPL", prices=[100, 100, 100])
    assert result == "sideways"


# --- detect_with_metrics ---------------------------------------------


def test_detect_with_metrics_no_data(detector):
    out = detector.detect_with_metrics("AAPL", prices=[])
    assert out["reason"] == "no_data"


def test_detect_with_metrics_flat(monkeypatch, detector):
    monkeypatch.setattr(
        pd.Series, "pct_change", lambda self: pd.Series([], dtype="float64")
    )
    out = detector.detect_with_metrics("AAPL", prices=[100, 100])
    assert out["reason"] == "flat"


def test_detect_with_metrics_bad_data(monkeypatch, detector):
    monkeypatch.setattr(
        pd.Series, "std", lambda *_: (_ for _ in ()).throw(Exception("bad"))
    )
    out = detector.detect_with_metrics("AAPL", prices=[100, 101, 102])
    assert out["reason"] == "bad_data"


def test_detect_with_metrics_normal(monkeypatch, detector):
    monkeypatch.setattr(detector, "detect", lambda *_: "bull")
    monkeypatch.setattr(pd.Series, "mean", lambda *_: 0.05)
    monkeypatch.setattr(pd.Series, "std", lambda *_: 0.01)

    class DummySeries(pd.Series):
        def sum(self, *_, **__):
            return 999.0

    monkeypatch.setattr(pd.Series, "abs", lambda self: DummySeries([1.0, 1.0]))
    out = detector.detect_with_metrics("AAPL", prices=[100, 105, 110])
    assert set(out) >= {"regime", "avg_return", "volatility", "n_samples"}
    assert out["regime"] == "bull"


# --- DB fetch paths --------------------------------------------------


def test_get_prices_db_success(monkeypatch):
    now = datetime.utcnow()
    dummy_prices = [
        DummyPrice(100, timestamp=now - timedelta(days=2)),
        DummyPrice(110, timestamp=now - timedelta(days=1)),
    ]
    monkeypatch.setattr(
        "hybrid_ai_trading.risk.regime_detector.SessionLocal",
        lambda: DummySession(dummy_prices),
    )
    d = RegimeDetector()
    s = d._get_prices("AAPL")
    assert not s.empty


def test_get_prices_db_error(monkeypatch):
    monkeypatch.setattr(
        "hybrid_ai_trading.risk.regime_detector.SessionLocal", lambda: BrokenSession()
    )
    d = RegimeDetector()
    s = d._get_prices("AAPL")
    assert s.empty


# --- Confidence + reset ----------------------------------------------


def test_confidence_all(monkeypatch):
    d = RegimeDetector()
    monkeypatch.setattr(d, "detect", lambda *_: "bull")
    assert d.confidence("AAPL") == 0.9
    monkeypatch.setattr(d, "detect", lambda *_: "bear")
    assert d.confidence("AAPL") == 0.1
    monkeypatch.setattr(d, "detect", lambda *_: "crisis")
    assert d.confidence("AAPL") == 0.3
    monkeypatch.setattr(d, "detect", lambda *_: "transition")
    assert d.confidence("AAPL") == 0.5
    monkeypatch.setattr(d, "detect", lambda *_: "sideways")
    assert d.confidence("AAPL") == 0.5
    d.enabled = False
    assert d.confidence("AAPL") == 0.0


def test_reset_history(detector):
    detector.history["AAPL"] = ["bull"]
    detector.reset()
    assert detector.history == {}
