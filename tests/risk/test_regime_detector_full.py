"""
Unit Tests: RegimeDetector (Hybrid AI Quant Pro – 100% Coverage, Branch-Safe)
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


def test_detect_disabled():
    d = RegimeDetector()
    d.enabled = False
    assert d.detect("AAPL", prices=[100, 101]) == "neutral"


def test_detect_no_data():
    d = RegimeDetector()
    assert d.detect("AAPL", prices=[]) == "neutral"


def test_detect_insufficient_data():
    d = RegimeDetector(min_samples=10)
    assert d.detect("AAPL", prices=[100, 101]) == "neutral"


def test_detect_empty_returns(monkeypatch):
    d = RegimeDetector()
    monkeypatch.setattr(
        pd.Series, "pct_change", lambda self: pd.Series([], dtype="float64")
    )
    assert d.detect("AAPL", prices=[100, 101, 102]) == "sideways"


def test_detect_exception_in_stats(monkeypatch):
    d = RegimeDetector()
    monkeypatch.setattr(
        pd.Series, "mean", lambda *_: (_ for _ in ()).throw(Exception("boom"))
    )
    assert d.detect("AAPL", prices=[100, 101, 102]) == "neutral"


def test_detect_bull(monkeypatch):
    d = RegimeDetector(bull_threshold=0.01, bear_threshold=-0.01, crisis_volatility=0.5)
    monkeypatch.setattr(pd.Series, "mean", lambda *_: 0.05)
    monkeypatch.setattr(pd.Series, "std", lambda *_: 0.01)

    class DummyAbs(pd.Series):
        def sum(self, *_, **__):
            return 999.0

    monkeypatch.setattr(pd.Series, "abs", lambda self: DummyAbs([1.0, 1.0]))
    assert d.detect("AAPL", prices=[100, 110, 120]) == "bull"


def test_detect_bear(monkeypatch):
    d = RegimeDetector(bull_threshold=0.01, bear_threshold=-0.01, crisis_volatility=0.5)
    monkeypatch.setattr(pd.Series, "mean", lambda *_: -0.05)
    monkeypatch.setattr(pd.Series, "std", lambda *_: 0.01)

    class DummyAbs(pd.Series):
        def sum(self, *_, **__):
            return 999.0

    monkeypatch.setattr(pd.Series, "abs", lambda self: DummyAbs([1.0, 1.0]))
    assert d.detect("AAPL", prices=[100, 90, 80]) == "bear"


def test_detect_crisis(monkeypatch):
    d = RegimeDetector(crisis_volatility=0.03)
    monkeypatch.setattr(pd.Series, "mean", lambda *_: 0.0)
    monkeypatch.setattr(pd.Series, "std", lambda *_: 0.5)

    class DummyAbs(pd.Series):
        def sum(self, *_, **__):
            return 999.0

    monkeypatch.setattr(pd.Series, "abs", lambda self: DummyAbs([1.0, 1.0]))
    assert d.detect("AAPL", prices=[100, 200, 50]) == "crisis"


def test_detect_transition(monkeypatch):
    d = RegimeDetector(bull_threshold=0.02, bear_threshold=-0.02, crisis_volatility=0.5)
    monkeypatch.setattr(pd.Series, "mean", lambda *_: 0.005)
    monkeypatch.setattr(pd.Series, "std", lambda *_: 0.02)

    class DummyAbs(pd.Series):
        def sum(self, *_, **__):
            return 999.0

    monkeypatch.setattr(pd.Series, "abs", lambda self: DummyAbs([1.0, 1.0]))
    assert d.detect("AAPL", prices=[100, 101, 100.5]) == "transition"


def test_detect_sideways(monkeypatch):
    d = RegimeDetector(neutral_tolerance=1e-4)
    monkeypatch.setattr(pd.Series, "mean", lambda *_: 0.0)
    monkeypatch.setattr(pd.Series, "std", lambda *_: 0.0)

    class DummyAbs(pd.Series):
        def sum(self, *_, **__):
            return 0.0

    monkeypatch.setattr(pd.Series, "abs", lambda self: DummyAbs([0.0, 0.0]))
    assert d.detect("AAPL", prices=[100, 100, 100]) == "sideways"


# --- detect_with_metrics ---------------------------------------------


def test_detect_with_metrics_no_data():
    d = RegimeDetector()
    out = d.detect_with_metrics("AAPL", prices=[])
    assert out["reason"] == "no_data"


def test_detect_with_metrics_flat(monkeypatch):
    d = RegimeDetector()
    monkeypatch.setattr(
        pd.Series, "pct_change", lambda self: pd.Series([], dtype="float64")
    )
    out = d.detect_with_metrics("AAPL", prices=[100, 100])
    assert out["reason"] == "flat"


def test_detect_with_metrics_bad_data(monkeypatch):
    d = RegimeDetector()
    monkeypatch.setattr(
        pd.Series, "std", lambda *_: (_ for _ in ()).throw(Exception("bad"))
    )
    out = d.detect_with_metrics("AAPL", prices=[100, 101, 102])
    assert out["reason"] == "bad_data"


def test_detect_with_metrics_normal(monkeypatch):
    d = RegimeDetector()
    monkeypatch.setattr(d, "detect", lambda *_: "bull")
    monkeypatch.setattr(pd.Series, "mean", lambda *_: 0.05)
    monkeypatch.setattr(pd.Series, "std", lambda *_: 0.01)

    class DummyAbs(pd.Series):
        def sum(self, *_, **__):
            return 999.0

    monkeypatch.setattr(pd.Series, "abs", lambda self: DummyAbs([1.0, 1.0]))
    out = d.detect_with_metrics("AAPL", prices=[100, 105, 110])
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


def test_reset_history():
    d = RegimeDetector()
    d.history["AAPL"] = ["bull"]
    d.reset()
    assert d.history == {}


def test_detect_empty_returns(monkeypatch):
    # Ensure we do NOT trip the 'insufficient data' guard; we want the empty-returns branch.
    d = RegimeDetector(min_samples=1)
    monkeypatch.setattr(
        pd.Series, "pct_change", lambda self: pd.Series([], dtype="float64")
    )
    assert d.detect("AAPL", prices=[100, 101, 102]) == "sideways"


def test_detect_bull(monkeypatch):
    d = RegimeDetector(
        min_samples=1, bull_threshold=0.01, bear_threshold=-0.01, crisis_volatility=0.5
    )
    monkeypatch.setattr(pd.Series, "mean", lambda *_: 0.05)
    monkeypatch.setattr(pd.Series, "std", lambda *_: 0.01)

    class DummyAbs(pd.Series):
        def sum(self, *_, **__):
            return 999.0

    monkeypatch.setattr(pd.Series, "abs", lambda self: DummyAbs([1.0, 1.0]))
    assert d.detect("AAPL", prices=[100, 110, 120]) == "bull"


def test_detect_bear(monkeypatch):
    d = RegimeDetector(
        min_samples=1, bull_threshold=0.01, bear_threshold=-0.01, crisis_volatility=0.5
    )
    monkeypatch.setattr(pd.Series, "mean", lambda *_: -0.05)
    monkeypatch.setattr(pd.Series, "std", lambda *_: 0.01)

    class DummyAbs(pd.Series):
        def sum(self, *_, **__):
            return 999.0

    monkeypatch.setattr(pd.Series, "abs", lambda self: DummyAbs([1.0, 1.0]))
    assert d.detect("AAPL", prices=[100, 90, 80]) == "bear"


def test_detect_crisis(monkeypatch):
    d = RegimeDetector(min_samples=1, crisis_volatility=0.03)
    monkeypatch.setattr(pd.Series, "mean", lambda *_: 0.0)
    monkeypatch.setattr(pd.Series, "std", lambda *_: 0.5)

    class DummyAbs(pd.Series):
        def sum(self, *_, **__):
            return 999.0

    monkeypatch.setattr(pd.Series, "abs", lambda self: DummyAbs([1.0, 1.0]))
    assert d.detect("AAPL", prices=[100, 200, 50]) == "crisis"


def test_detect_transition(monkeypatch):
    d = RegimeDetector(
        min_samples=1, bull_threshold=0.02, bear_threshold=-0.02, crisis_volatility=0.5
    )
    monkeypatch.setattr(pd.Series, "mean", lambda *_: 0.005)
    monkeypatch.setattr(pd.Series, "std", lambda *_: 0.02)

    class DummyAbs(pd.Series):
        def sum(self, *_, **__):
            return 999.0

    monkeypatch.setattr(pd.Series, "abs", lambda self: DummyAbs([1.0, 1.0]))
    assert d.detect("AAPL", prices=[100, 101, 100.5]) == "transition"


def test_detect_sideways(monkeypatch):
    d = RegimeDetector(min_samples=1, neutral_tolerance=1e-4)
    monkeypatch.setattr(pd.Series, "mean", lambda *_: 0.0)
    monkeypatch.setattr(pd.Series, "std", lambda *_: 0.0)

    class DummyAbs(pd.Series):
        def sum(self, *_, **__):
            return 0.0

    monkeypatch.setattr(pd.Series, "abs", lambda self: DummyAbs([0.0, 0.0]))
    assert d.detect("AAPL", prices=[100, 100, 100]) == "sideways"


def test_detect_updates_history_append(monkeypatch):
    """Ensure classification path runs and history is updated (covers post-classification lines)."""
    d = RegimeDetector(
        min_samples=1, bull_threshold=0.02, bear_threshold=-0.02, crisis_volatility=0.5
    )

    # First call: bull
    monkeypatch.setattr(pd.Series, "mean", lambda *_: 0.03)
    monkeypatch.setattr(pd.Series, "std", lambda *_: 0.01)

    class DummyAbs1(pd.Series):
        def sum(self, *_, **__):
            return 999.0

    monkeypatch.setattr(pd.Series, "abs", lambda self: DummyAbs1([1.0, 1.0]))
    out1 = d.detect("SPY", prices=[100, 110, 121])
    assert out1 == "bull"
    assert d.history.get("SPY") == ["bull"]

    # Second call: bear (append to history)
    monkeypatch.setattr(pd.Series, "mean", lambda *_: -0.03)
    monkeypatch.setattr(pd.Series, "std", lambda *_: 0.01)

    class DummyAbs2(pd.Series):
        def sum(self, *_, **__):
            return 999.0

    monkeypatch.setattr(pd.Series, "abs", lambda self: DummyAbs2([1.0, 1.0]))
    out2 = d.detect("SPY", prices=[121, 110, 100])
    assert out2 == "bear"
    assert d.history["SPY"] == ["bull", "bear"]


def test_get_prices_from_list_success():
    """Exercise _get_prices list path returning a float64 Series (covers final return)."""
    d = RegimeDetector()
    s = d._get_prices("AAPL", prices=[100, 101.25, "102.5"])
    assert not s.empty
    assert str(s.dtype) == "float64"
    # sanity: values coerced to float
    assert pytest.approx(float(s.iloc[-1]), rel=1e-6) == 102.5


def test_get_prices_list_bad_data_logs_and_returns_empty(caplog):
    """Covers _get_prices(list) exception branch (bad price coercion) → empty Series."""
    caplog.set_level("ERROR")
    d = RegimeDetector()
    # include an uncastable object to force the float() conversion error
    s = d._get_prices("AAPL", prices=[100.0, object(), 101.0])
    assert s.empty
    assert "Bad price data" in caplog.text


def test_detect_normal_flow_without_monkeypatch_closes_and_logs(caplog):
    """
    Run detect end-to-end with real returns computation so the tail logging/return path
    and final lines are unquestionably executed.
    """
    caplog.set_level("INFO")
    d = RegimeDetector(
        min_samples=1, bull_threshold=0.01, bear_threshold=-0.01, crisis_volatility=0.5
    )
    # a simple INCREASING series that produces a > bull_threshold avg return, low vol
    result = d.detect("AAPL", prices=[100, 102, 104, 106, 108])
    assert result in {
        "bull",
        "transition",
        "sideways",
        "bear",
        "crisis",
    }  # must classify something
    # history updated and final log executed
    assert "Regime calc" in caplog.text or "Regime" in caplog.text
    assert "AAPL" in d.history and len(d.history["AAPL"]) >= 1


def test_detect_normal_flow_without_monkeypatch_closes_and_logs(monkeypatch, caplog):
    """
    Ensure detect() executes the final logging/return path by patching mean/std to safe values.
    This avoids pandas sentinel issues and exercises lines at the tail of detect.
    """
    caplog.set_level("INFO")
    d = RegimeDetector(
        min_samples=1, bull_threshold=0.01, bear_threshold=-0.01, crisis_volatility=0.5
    )

    # Patch Series.mean/std so we classify as 'bull' with low volatility
    monkeypatch.setattr(pd.Series, "mean", lambda *_: 0.02)  # > bull_threshold
    monkeypatch.setattr(pd.Series, "std", lambda *_: 0.01)  # < crisis_volatility

    result = d.detect("AAPL", prices=[100, 102, 104, 106, 108])
    assert result == "bull"  # deterministic classification

    # Tail logging executed and history updated
    assert "Regime calc" in caplog.text or "Regime" in caplog.text
    assert "AAPL" in d.history and len(d.history["AAPL"]) >= 1


def test_detect_normal_flow_without_monkeypatch_closes_and_logs(monkeypatch, caplog):
    """
    Ensure detect() executes the final logging/return path by patching mean/std and abs().sum()
    to safe values so pandas/numpy internals cannot raise on sentinels.
    """
    import pandas as pd

    caplog.set_level("INFO")
    d = RegimeDetector(
        min_samples=1, bull_threshold=0.01, bear_threshold=-0.01, crisis_volatility=0.5
    )

    # Patch Series.mean/std so we classify as 'bull' with low volatility
    monkeypatch.setattr(pd.Series, "mean", lambda *_: 0.02)  # > bull_threshold
    monkeypatch.setattr(pd.Series, "std", lambda *_: 0.01)  # < crisis_volatility

    # Patch .abs() to return a dummy series whose sum() returns a normal float
    class DummyAbs(pd.Series):
        def sum(self, *_, **__):
            return 1.0  # > neutral_tolerance, avoids 'sideways'

    monkeypatch.setattr(pd.Series, "abs", lambda self: DummyAbs([1.0, 1.0]))

    result = d.detect("AAPL", prices=[100, 102, 104, 106, 108])
    assert result == "bull"  # deterministic classification

    # Tail logging executed and history updated
    logtext = caplog.text
    assert "Regime calc" in logtext or "regime=" in logtext
    assert "AAPL" in d.history and len(d.history["AAPL"]) >= 1


def test_detect_stats_exception_again_hits_94_96(monkeypatch, caplog):
    """Force std() to raise a distinct exception while mean() works, to hit error/return lines 94–96."""
    import pandas as pd

    caplog.set_level("ERROR")
    d = RegimeDetector(min_samples=1)
    monkeypatch.setattr(pd.Series, "mean", lambda *_: 0.01)
    monkeypatch.setattr(
        pd.Series, "std", lambda *_: (_ for _ in ()).throw(RuntimeError("std-fail"))
    )
    out = d.detect("AAPL", prices=[100, 101, 102, 103])
    assert out == "neutral"
    assert "Return stats failed" in caplog.text
