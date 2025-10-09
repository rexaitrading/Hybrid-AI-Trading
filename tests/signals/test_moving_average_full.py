"""
Unit Tests: Moving Average Signal (Hybrid AI Quant Pro v23.7 – Hedge-Fund Grade, 100% Coverage)
-----------------------------------------------------------------------------------------------
Covers ALL branches of moving_average_signal:
- Empty bars
- Not enough bars
- Missing 'c' field (closes.empty)
- Parse error (non-numeric values)
- NaN closes
- NaN SMA values
- BUY branch
- SELL branch
- HOLD branch (equal SMA / no crossover)
- Exception handling (rolling failure)
- Wrapper class consistency
"""

import pandas as pd
import pytest

from hybrid_ai_trading.signals.moving_average import (
    moving_average_signal,
    MovingAverageSignal,
)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def make_bars(n: int = 30, trend: str = "up"):
    """Generate synthetic close bars for testing."""
    if trend == "up":
        return [{"c": i} for i in range(1, n + 1)]
    if trend == "down":
        return [{"c": i} for i in range(n, 0, -1)]
    return [{"c": 50}] * n  # flat


# ----------------------------------------------------------------------
# Guard Branches
# ----------------------------------------------------------------------
def test_empty_bars():
    assert moving_average_signal([]) == "HOLD"


def test_not_enough_bars():
    bars = [{"c": i} for i in range(5)]
    assert moving_average_signal(bars, short_window=3, long_window=10) == "HOLD"


def test_missing_close_field():
    bars = [{"o": 1, "h": 2}] * 30
    assert moving_average_signal(bars, short_window=3, long_window=10) == "HOLD"


def test_parse_error_in_close():
    bars = [{"c": "bad"}] * 30
    assert moving_average_signal(bars, short_window=3, long_window=10) == "HOLD"


def test_nan_closes():
    bars = [{"c": float("nan")}] * 30
    assert moving_average_signal(bars, short_window=3, long_window=10) == "HOLD"


# ----------------------------------------------------------------------
# Core Decision Logic
# ----------------------------------------------------------------------
def test_forced_buy_branch(monkeypatch):
    """Force short MA > long MA → BUY."""
    bars = make_bars(30)

    def fake_rolling(self, window, *args, **kwargs):
        class FakeRolling:
            def mean(_self, *_a, **_k):
                if window == 3:   # short MA
                    return pd.Series([1.0, 2.0], index=self.index[-2:])
                if window == 10:  # long MA
                    return pd.Series([2.0, 1.5], index=self.index[-2:])
                return pd.Series([1.0] * len(self), index=self.index)
        return FakeRolling()

    monkeypatch.setattr(pd.Series, "rolling", fake_rolling)
    assert moving_average_signal(bars, short_window=3, long_window=10) == "BUY"


def test_forced_sell_branch(monkeypatch):
    """Force short MA < long MA → SELL."""
    bars = make_bars(30)

    def fake_rolling(self, window, *args, **kwargs):
        class FakeRolling:
            def mean(_self, *_a, **_k):
                if window == 3:   # short MA
                    return pd.Series([3.0, 1.0], index=self.index[-2:])
                if window == 10:  # long MA
                    return pd.Series([2.0, 2.5], index=self.index[-2:])
                return pd.Series([1.0] * len(self), index=self.index)
        return FakeRolling()

    monkeypatch.setattr(pd.Series, "rolling", fake_rolling)
    assert moving_average_signal(bars, short_window=3, long_window=10) == "SELL"


def test_hold_equal_forced(monkeypatch):
    """Force short MA == long MA → HOLD."""
    bars = make_bars(30)

    def fake_rolling(self, window, *args, **kwargs):
        class FakeRolling:
            def mean(_self, *_a, **_k):
                return pd.Series([2.0] * len(self), index=self.index)
        return FakeRolling()

    monkeypatch.setattr(pd.Series, "rolling", fake_rolling)
    assert moving_average_signal(bars, short_window=3, long_window=10) == "HOLD"


def test_nan_sma(monkeypatch):
    """Force rolling().mean() to produce NaN → HOLD."""
    bars = make_bars(30)

    def fake_rolling(self, window, *args, **kwargs):
        class FakeRolling:
            def mean(_self, *_a, **_k):
                values = [1.0] * (len(self) - 1) + [float("nan")]
                return pd.Series(values, index=self.index)
        return FakeRolling()

    monkeypatch.setattr(pd.Series, "rolling", fake_rolling)
    assert moving_average_signal(bars, short_window=3, long_window=10) == "HOLD"


def test_rolling_failure(monkeypatch):
    """Simulate exception in rolling mean → triggers 'failed rolling'."""
    bars = make_bars(30)

    def boom_rolling(self, window, *args, **kwargs):
        raise Exception("boom")

    monkeypatch.setattr(pd.Series, "rolling", boom_rolling)
    out = MovingAverageSignal(short_window=3, long_window=10).generate("SYM", bars)
    assert out["signal"] == "HOLD"
    assert out["reason"] == "failed rolling"


# ----------------------------------------------------------------------
# Wrapper consistency
# ----------------------------------------------------------------------
def test_wrapper_class_consistency():
    bars = make_bars(50, trend="up")
    f_result = moving_average_signal(bars)
    c_result = MovingAverageSignal().generate("AAPL", bars)["signal"]
    assert f_result == c_result
    assert c_result in ("BUY", "SELL", "HOLD")
