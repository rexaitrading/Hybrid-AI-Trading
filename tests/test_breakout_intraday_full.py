"""
Unit Tests: Breakout Intraday Signal (Hybrid AI Quant Pro v22.3 – Absolute 100% Coverage)
-----------------------------------------------------------------------------------------
Covers ALL branches of breakout_intraday:
- BUY  (last >= high)
- SELL (last <= low)
- SELL tie priority (last == high == low)
- HOLD strictly inside range
- Guard branches:
  * No bars
  * Invalid window
  * Not enough bars
  * Missing close field
  * Parse exception
  * NaN values
- Audit mode: returns tuple (decision, price, high, low)
"""

import logging
import math
import pytest
from hybrid_ai_trading.signals.breakout_intraday import breakout_intraday


def make_bars(prices):
    """Helper: convert a list of closes into bar dicts."""
    return [{"c": p} for p in prices]


# --- Core Paths ---

def test_buy_breakout_above_or_equal(caplog):
    caplog.set_level(logging.INFO)
    prices = [10] * 20 + [31]  # last == high
    result = breakout_intraday(make_bars(prices), window=20)
    assert result == "BUY"
    assert "Breakout BUY" in caplog.text


def test_sell_breakout_below_or_equal(caplog):
    caplog.set_level(logging.INFO)
    prices = [20] * 20 + [5]  # last == low
    result = breakout_intraday(make_bars(prices), window=20)
    assert result == "SELL"
    assert "Breakout SELL" in caplog.text


def test_sell_tie_priority(caplog):
    caplog.set_level(logging.INFO)
    prices = [50] * 20  # tie case: last == high == low
    result = breakout_intraday(make_bars(prices), window=20)
    assert result == "SELL"  # ✅ SELL priority
    assert "Tie case" in caplog.text


def test_hold_inside_range(caplog):
    caplog.set_level(logging.DEBUG)
    prices = list(range(1, 21)) + [15]  # inside [1,20]
    result = breakout_intraday(make_bars(prices), window=20)
    assert result == "HOLD"
    assert "Inside range" in caplog.text


# --- Guard Cases ---

def test_no_bars(caplog):
    caplog.set_level(logging.INFO)
    result = breakout_intraday([], window=20)
    assert result == "HOLD"
    assert "No bars" in caplog.text


def test_invalid_window(caplog):
    caplog.set_level(logging.INFO)
    result = breakout_intraday(make_bars([1, 2, 3]), window=0)
    assert result == "HOLD"
    assert "Invalid window" in caplog.text


def test_not_enough_bars(caplog):
    caplog.set_level(logging.INFO)
    result = breakout_intraday(make_bars([1, 2, 3]), window=10)
    assert result == "HOLD"
    assert "Not enough bars" in caplog.text


def test_missing_close_field(caplog):
    caplog.set_level(logging.WARNING)
    bars = [{"o": 1, "h": 2, "l": 0}]  # missing "c"
    result = breakout_intraday(bars, window=1)
    assert result == "HOLD"
    assert "Missing close price" in caplog.text


def test_parse_exception_branch(caplog):
    caplog.set_level(logging.ERROR)
    bars = [{"c": "bad"} for _ in range(20)]  # cannot parse float
    result = breakout_intraday(bars, window=20)
    assert result == "HOLD"
    assert "Failed to parse close prices" in caplog.text


def test_nan_branch(caplog):
    caplog.set_level(logging.WARNING)
    bars = make_bars([float("nan")] * 20)
    result = breakout_intraday(bars, window=20)
    assert result == "HOLD"
    assert "NaN detected" in caplog.text


# --- Audit Mode Coverage ---

def test_audit_buy_branch():
    prices = [10] * 20 + [31]
    decision, price, rh, rl = breakout_intraday(make_bars(prices), window=20, audit=True)
    assert decision == "BUY"
    assert price == 31.0
    assert rh == 31.0
    assert rl == 10.0


def test_audit_sell_branch():
    prices = [20] * 20 + [5]
    decision, price, rh, rl = breakout_intraday(make_bars(prices), window=20, audit=True)
    assert decision == "SELL"
    assert price == 5.0
    assert rh == 20.0
    assert rl == 5.0


def test_audit_hold_branch():
    prices = list(range(1, 21)) + [15]
    decision, price, rh, rl = breakout_intraday(make_bars(prices), window=20, audit=True)
    assert decision == "HOLD"
    assert rl < price < rh
