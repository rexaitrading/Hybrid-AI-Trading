"""
Unit Tests: Breakout V1 (Hybrid AI Quant Pro v22.6 – AAA Final 100% Coverage)
=============================================================================
- Validates ALL branches of breakout_v1.py
- Guards: empty bars, invalid window, insufficient bars, window=1
- Parse errors + NaN handling
- Signal logic: BUY, SELL, HOLD (edge cases)
- Audit mode tuple return
- Wrapper breakout_signal: with bars, invalid bars, fetch fail, empty fetch
"""

import pytest
import logging
from unittest.mock import patch
import importlib

# Import breakout_v1 module dynamically to ensure correct path
breakout_v1 = importlib.import_module("hybrid_ai_trading.signals.breakout_v1")


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def make_bars(prices):
    """Utility to wrap prices into list of dict bars with 'c' field."""
    return [{"c": p} for p in prices]


# -------------------------------------------------------------------
# Guard / Input Branches
# -------------------------------------------------------------------
def test_no_bars(caplog):
    caplog.set_level(logging.INFO)
    result = breakout_v1.breakout_v1([])
    assert result == "HOLD"
    assert "no bars" in caplog.text.lower()


def test_invalid_window(caplog):
    caplog.set_level(logging.INFO)
    result = breakout_v1.breakout_v1(make_bars([1, 2, 3]), window=0)
    assert result == "HOLD"
    assert "invalid" in caplog.text.lower()


def test_not_enough_bars(caplog):
    caplog.set_level(logging.INFO)
    result = breakout_v1.breakout_v1(make_bars([1, 2]), window=5)
    assert result == "HOLD"
    assert "not enough bars" in caplog.text.lower()


def test_window_one_edge_case(caplog):
    caplog.set_level(logging.INFO)
    result = breakout_v1.breakout_v1(make_bars([42]), window=1)
    assert result == "HOLD"
    assert "window=1" in caplog.text.lower()


# -------------------------------------------------------------------
# Parse & NaN Handling
# -------------------------------------------------------------------
def test_parse_error(caplog):
    caplog.set_level(logging.ERROR)
    bars = [{"c": "bad"}]
    result = breakout_v1.breakout_v1(bars, window=1)
    assert result == "HOLD"
    assert "parse" in caplog.text.lower()


def test_nan_values(caplog):
    caplog.set_level(logging.WARNING)
    bars = make_bars([float("nan"), 5, 10])
    result = breakout_v1.breakout_v1(bars, window=3)
    assert result == "HOLD"
    assert "nan" in caplog.text.lower()


# -------------------------------------------------------------------
# Core Signal Decisions
# -------------------------------------------------------------------
def test_sell_tie_priority(caplog):
    caplog.set_level(logging.INFO)
    bars = make_bars([50, 50, 50])  # tie triggers SELL bias
    result = breakout_v1.breakout_v1(bars, window=3)
    assert result == "SELL"
    assert "sell" in caplog.text.lower()


def test_sell_when_strictly_below_low(caplog):
    caplog.set_level(logging.INFO)
    bars = make_bars([10, 12, 4])  # last close < rolling low
    result = breakout_v1.breakout_v1(bars, window=3)
    assert result == "SELL"
    assert "sell" in caplog.text.lower()


def test_hold_when_equal_low(caplog):
    caplog.set_level(logging.INFO)
    bars = make_bars([10, 12, 10])  # last close == rolling low
    result = breakout_v1.breakout_v1(bars, window=3)
    assert result == "HOLD"
    assert "hold" in caplog.text.lower()


def test_buy_when_above_high(caplog):
    caplog.set_level(logging.INFO)
    bars = make_bars([1, 2, 10])  # last close > rolling high
    result = breakout_v1.breakout_v1(bars, window=3)
    assert result == "BUY"
    assert "buy" in caplog.text.lower()


def test_hold_retest_at_high(caplog):
    caplog.set_level(logging.INFO)
    bars = make_bars([1, 5, 5])  # last close == high
    result = breakout_v1.breakout_v1(bars, window=3)
    assert result == "HOLD"
    assert "hold" in caplog.text.lower()


def test_hold_inside_range(caplog):
    caplog.set_level(logging.DEBUG)
    bars = make_bars([1, 10, 5])  # inside prior range
    result = breakout_v1.breakout_v1(bars, window=3)
    assert result == "HOLD"
    assert "hold" in caplog.text.lower()


# -------------------------------------------------------------------
# Audit Mode
# -------------------------------------------------------------------
def test_audit_mode_returns_tuple():
    bars = make_bars([1, 10, 5])
    decision, price, rh, rl = breakout_v1.breakout_v1(bars, window=3, audit=True)
    assert decision in ["BUY", "SELL", "HOLD"]
    assert isinstance(price, float)
    assert isinstance(rh, float)
    assert isinstance(rl, float)


# -------------------------------------------------------------------
# Wrapper breakout_signal
# -------------------------------------------------------------------
def test_wrapper_with_bars_direct():
    bars = [{"c": 1}, {"c": 2}, {"c": 3}]
    result = breakout_v1.breakout_signal("AAPL", bars=bars)
    assert result in ["BUY", "SELL", "HOLD"]


def test_wrapper_invalid_bar_format(caplog):
    caplog.set_level(logging.ERROR)
    bars = [{"x": 1}]  # missing "c" field
    result = breakout_v1.breakout_signal("AAPL", bars=bars)
    assert result == "HOLD"
    assert "invalid" in caplog.text.lower()


def test_wrapper_fetch_fails(monkeypatch, caplog):
    caplog.set_level(logging.ERROR)
    monkeypatch.setattr(
        breakout_v1,
        "get_ohlcv_latest",
        lambda *a, **k: (_ for _ in ()).throw(Exception("boom")),
    )
    result = breakout_v1.breakout_signal("AAPL")
    assert result == "HOLD"
    assert "fetch failed" in caplog.text.lower()


def test_wrapper_empty_bars(monkeypatch):
    monkeypatch.setattr(breakout_v1, "get_ohlcv_latest", lambda *a, **k: [])
    result = breakout_v1.breakout_signal("AAPL")
    assert result == "HOLD"
