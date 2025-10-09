"""
Unit Tests: BreakoutIntradaySignal (Hybrid AI Quant Pro v24.1 – Hedge-Fund Grade, 100% Coverage)
-----------------------------------------------------------------------------------------------
Covers ALL branches of breakout_intraday:
- no_bars
- invalid_window
- insufficient_data
- parse_error
- invalid_data (missing fields)
- nan_detected
- breakout_up
- breakout_down
- tie_case
- inside_range
- wrapper: audit + non-audit, no bars
- wrapper: slice default branch
- logger debug/info/warning coverage
"""

import math
import pytest
from hybrid_ai_trading.signals.breakout_intraday import (
    BreakoutIntradaySignal,
    breakout_intraday,
)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def make_bars(closes, highs=None, lows=None):
    """Utility to build bar dicts with closes, highs, lows."""
    highs = highs or closes
    lows = lows or closes
    return [{"c": c, "h": h, "l": l} for c, h, l in zip(closes, highs, lows)]


# ----------------------------------------------------------------------
# Guard branches
# ----------------------------------------------------------------------
def test_no_bars():
    sig = BreakoutIntradaySignal(lookback=5)
    result = sig.generate("AAPL", [])
    assert result["signal"] == "HOLD"
    assert result["reason"] == "no_bars"


def test_invalid_window():
    sig = BreakoutIntradaySignal(lookback=0)
    result = sig.generate("AAPL", make_bars([1, 2, 3]))
    assert result["signal"] == "HOLD"
    assert result["reason"] == "invalid_window"


def test_insufficient_bars():
    sig = BreakoutIntradaySignal(lookback=10)
    result = sig.generate("AAPL", make_bars([1, 2, 3]))
    assert result["signal"] == "HOLD"
    assert result["reason"] == "insufficient_data"


def test_parse_error(monkeypatch):
    def bad_float(_): raise ValueError("bad")
    monkeypatch.setattr("builtins.float", bad_float)
    sig = BreakoutIntradaySignal(lookback=5)
    result = sig.generate("AAPL", make_bars([1, 2, 3, 4, 5, 6]))
    assert result["signal"] == "HOLD"
    assert result["reason"] == "parse_error"


def test_invalid_data_missing_fields():
    sig = BreakoutIntradaySignal(lookback=5)
    bars = [{"o": 1}] * 10
    result = sig.generate("AAPL", bars)
    assert result["signal"] == "HOLD"
    assert result["reason"] == "invalid_data"


def test_nan_detected():
    sig = BreakoutIntradaySignal(lookback=5)
    bars = make_bars([1, 2, math.nan, 4, 5])
    result = sig.generate("AAPL", bars)
    assert result["signal"] == "HOLD"
    assert result["reason"] == "nan_detected"


# ----------------------------------------------------------------------
# Decision logic
# ----------------------------------------------------------------------
def test_buy_breakout(caplog):
    sig = BreakoutIntradaySignal(lookback=5)
    bars = make_bars([1, 2, 3, 4, 10])
    caplog.set_level("INFO")
    result = sig.generate("AAPL", bars)
    assert result["signal"] == "BUY"
    assert result["reason"] == "breakout_up"
    assert "Breakout UP detected" in caplog.text


def test_sell_breakout(caplog):
    sig = BreakoutIntradaySignal(lookback=5)
    bars = make_bars([10, 9, 8, 7, 1])
    caplog.set_level("INFO")
    result = sig.generate("AAPL", bars)
    assert result["signal"] == "SELL"
    assert result["reason"] == "breakout_down"
    assert "Breakout DOWN detected" in caplog.text


def test_tie_case(caplog):
    sig = BreakoutIntradaySignal(lookback=5)
    bars = make_bars([5, 5, 5, 5, 5])
    caplog.set_level("INFO")
    result = sig.generate("AAPL", bars)
    assert result["signal"] == "SELL"
    assert result["reason"] == "tie_case"
    assert "Tie case" in caplog.text


def test_hold_inside_range(caplog):
    sig = BreakoutIntradaySignal(lookback=5)
    bars = make_bars([1, 10, 5, 7, 6])
    caplog.set_level("DEBUG")
    result = sig.generate("AAPL", bars)
    assert result["signal"] == "HOLD"
    assert result["reason"] == "inside_range"
    assert "Inside range" in caplog.text


# ----------------------------------------------------------------------
# Wrapper tests
# ----------------------------------------------------------------------
def test_wrapper_basic_modes():
    bars = make_bars([1, 2, 3, 4, 10])
    out = breakout_intraday(bars, window=5, audit=False)
    assert out in {"BUY", "SELL", "HOLD"}
    decision, close, high, low = breakout_intraday(bars, window=5, audit=True)
    assert decision in {"BUY", "SELL", "HOLD"}
    assert isinstance(close, float)
    assert isinstance(high, float)
    assert isinstance(low, float)


def test_wrapper_no_bars_all_modes():
    out = breakout_intraday([], window=5, audit=False)
    assert out == "HOLD"
    decision, close, high, low = breakout_intraday([], window=5, audit=True)
    assert decision == "HOLD"
    assert all(isinstance(v, float) for v in [close, high, low])


def test_wrapper_with_missing_fields():
    bars = [{"o": 1}] * 5
    decision, close, high, low = breakout_intraday(bars, window=5, audit=True)
    assert decision == "HOLD"
    assert close == 0.0
    assert high == 0.0
    assert low == 0.0


def test_wrapper_with_too_few_bars_triggers_default():
    bars = make_bars([42])  # only one bar
    decision, close, high, low = breakout_intraday(bars, window=5, audit=True)
    assert decision == "HOLD"
    assert high == close == low == 42.0
