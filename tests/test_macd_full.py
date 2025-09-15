"""
Unit Tests: MACD Signal (Hybrid AI Quant Pro v13.1 – Final 100% Coverage, Standardized Logs)
-------------------------------------------------------------------------------------------
Covers ALL branches:
- Empty bars
- Not enough bars
- Missing 'c' field
- NaN close values
- NaN MACD/Signal
- BUY branch
- SELL branch
- HOLD branch
- Exception handling
"""

import pytest
import logging
import pandas as pd
from hybrid_ai_trading.signals.macd import macd_signal


# ----------------------------
# Helpers
# ----------------------------
def make_bars(prices):
    return [{"c": p} for p in prices]


# ----------------------------
# Guard Branches
# ----------------------------
def test_empty_bars(caplog):
    caplog.set_level(logging.DEBUG)
    result = macd_signal([])
    assert result == "HOLD"
    assert "no bars" in caplog.text.lower()


def test_not_enough_bars(caplog):
    caplog.set_level(logging.DEBUG)
    bars = make_bars(range(10))
    result = macd_signal(bars, long=26, signal=9)
    assert result == "HOLD"
    assert "not enough bars" in caplog.text.lower()


def test_missing_close_field(caplog):
    caplog.set_level(logging.WARNING)
    bars = [{"o": 1, "h": 2}] * 50
    result = macd_signal(bars)
    assert result == "HOLD"
    assert "missing close" in caplog.text.lower()


def test_nan_close_values(caplog):
    caplog.set_level(logging.WARNING)
    bars = [{"c": float("nan")}] * 50
    result = macd_signal(bars)
    assert result == "HOLD"
    assert "nan detected" in caplog.text.lower()


# ----------------------------
# Decision Branches
# ----------------------------
def test_buy_branch(caplog):
    caplog.set_level(logging.INFO)
    bars = make_bars(list(range(1, 100)))  # uptrend
    result = macd_signal(bars)
    assert result == "BUY"
    assert "buy" in caplog.text.lower()


def test_sell_branch(caplog):
    caplog.set_level(logging.INFO)
    bars = make_bars(list(range(100, 0, -1)))  # downtrend
    result = macd_signal(bars)
    assert result == "SELL"
    assert "sell" in caplog.text.lower()


def test_hold_branch(caplog):
    caplog.set_level(logging.DEBUG)
    bars = make_bars([100] * 50)  # flat
    result = macd_signal(bars)
    assert result == "HOLD"
    assert "equals" in caplog.text.lower()


def test_nan_macd_signal(monkeypatch, caplog):
    caplog.set_level(logging.WARNING)

    bars = make_bars(range(50))

    # Patch pandas.Series.ewm → force NaNs
    class FakeEWM:
        def mean(self, *a, **k): return pd.Series([float("nan")] * len(bars))

    monkeypatch.setattr(pd.Series, "ewm", lambda *a, **k: FakeEWM())
    result = macd_signal(bars)
    assert result == "HOLD"
    assert "nan macd" in caplog.text.lower()


# ----------------------------
# Exception Handling
# ----------------------------
def test_exception_branch(monkeypatch, caplog):
    caplog.set_level(logging.ERROR)
    monkeypatch.setattr("pandas.DataFrame", lambda *_a, **_k: (_ for _ in ()).throw(Exception("boom")))
    bars = make_bars(range(50))
    result = macd_signal(bars)
    assert result == "HOLD"
    assert "failed" in caplog.text.lower()
