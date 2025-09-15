"""
Unit Tests: Breakout Intraday Signal (Hybrid AI Quant Pro v22.6 – Final 100% Coverage)
--------------------------------------------------------------------------------------
Covers all decision branches and guard rails with standardized log checks.
Rules:
    * BUY  if last close > rolling high
    * SELL if last close < rolling low
    * SELL priority on ties (price == high == low)
    * HOLD strictly inside range
Guards:
    * No bars
    * Invalid window
    * Not enough bars
    * Missing close field
    * Parse exception
    * NaN values
Audit=True → returns tuple (decision, price, rh, rl)
"""

import logging
import pytest
from hybrid_ai_trading.signals.breakout_intraday import breakout_intraday


def make_bars(prices):
    """Helper: convert price list to bars with 'c' close field."""
    return [{"c": p} for p in prices]


# === Core Logic Tests ===

def test_buy_breakout_above(caplog):
    caplog.set_level(logging.INFO)
    prices = [10] * 20 + [30]
    result = breakout_intraday(make_bars(prices), window=20)
    assert result == "BUY"
    assert "buy" in caplog.text.lower()


def test_sell_breakout_below(caplog):
    caplog.set_level(logging.INFO)
    prices = [100] * 20 + [50]
    result = breakout_intraday(make_bars(prices), window=20)
    assert result == "SELL"
    assert "sell" in caplog.text.lower()


def test_sell_tie_priority(caplog):
    caplog.set_level(logging.INFO)
    prices = [50] * 20  # tie case: price == high == low
    result = breakout_intraday(make_bars(prices), window=20)
    assert result == "SELL"  # ✅ SELL priority
    assert "sell" in caplog.text.lower()


def test_hold_inside_range(caplog):
    caplog.set_level(logging.DEBUG)
    prices = list(range(1, 21)) + [15]  # inside 1–20
    result = breakout_intraday(make_bars(prices), window=20)
    assert result == "HOLD"
    assert "hold" in caplog.text.lower()


# === Guard Branches ===

def test_no_bars(caplog):
    caplog.set_level(logging.INFO)
    result = breakout_intraday([], window=20)
    assert result == "HOLD"
    assert "no bars" in caplog.text.lower()


def test_invalid_window(caplog):
    caplog.set_level(logging.INFO)
    result = breakout_intraday(make_bars([1, 2, 3]), window=0)
    assert result == "HOLD"
    assert "invalid" in caplog.text.lower()


def test_not_enough_bars(caplog):
    caplog.set_level(logging.INFO)
    result = breakout_intraday(make_bars([1, 2, 3]), window=10)
    assert result == "HOLD"
    assert "not enough bars" in caplog.text.lower()


def test_missing_close_field(caplog):
    caplog.set_level(logging.WARNING)
    bars = [{"o": 1, "h": 2, "l": 0}]  # no 'c'
    result = breakout_intraday(bars, window=1)
    assert result == "HOLD"
    assert "missing" in caplog.text.lower()


def test_parse_exception_branch(caplog):
    caplog.set_level(logging.ERROR)
    bars = [{"c": "bad"} for _ in range(20)]
    result = breakout_intraday(bars, window=20)
    assert result == "HOLD"
    assert "parse" in caplog.text.lower()


def test_nan_branch(caplog):
    caplog.set_level(logging.WARNING)
    bars = make_bars([float("nan")] * 20)
    result = breakout_intraday(bars, window=20)
    assert result == "HOLD"
    assert "nan" in caplog.text.lower()


# === Audit Mode Tests ===

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
