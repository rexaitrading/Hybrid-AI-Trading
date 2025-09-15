"""
Unit Tests: RSI Signal (Hybrid AI Quant Pro v16.1 – Final 100% Coverage, Standardized Logs)
------------------------------------------------------------------------------------------
Covers ALL branches:
- Empty bars
- Not enough bars
- Missing 'c' field
- NaN close values
- BUY (<30)
- SELL (>70)
- HOLD (inside range)
- Loss=0 fallback: positive gain → SELL
- Loss=0 fallback: non-positive gain → BUY
- Exception handling
"""

import pytest
import logging
import pandas as pd
from hybrid_ai_trading.signals.rsi_signal import rsi_signal


# ----------------------------
# Helper
# ----------------------------
def make_bars(prices):
    return [{"c": p} for p in prices]


# ----------------------------
# Guard Branches
# ----------------------------
def test_empty_bars(caplog):
    caplog.set_level(logging.DEBUG)
    result = rsi_signal([])
    assert result == "HOLD"
    assert "no bars" in caplog.text.lower()


def test_not_enough_bars(caplog):
    caplog.set_level(logging.DEBUG)
    bars = [{"c": i} for i in range(10)]
    result = rsi_signal(bars, period=14)
    assert result == "HOLD"
    assert "not enough bars" in caplog.text.lower()


def test_missing_close_field(caplog):
    caplog.set_level(logging.WARNING)
    bars = [{"o": 1, "h": 2}] * 20
    result = rsi_signal(bars)
    assert result == "HOLD"
    assert "missing close" in caplog.text.lower()


def test_nan_close_values(caplog):
    caplog.set_level(logging.WARNING)
    bars = [{"c": float("nan")}] * 20
    result = rsi_signal(bars)
    assert result == "HOLD"
    assert "nan" in caplog.text.lower()


# ----------------------------
# Core Decisions
# ----------------------------
def test_buy_branch(caplog):
    caplog.set_level(logging.INFO)
    prices = list(range(50, 80)) + [20]  # oversold drop
    result = rsi_signal(make_bars(prices), period=14)
    assert result == "BUY"
    assert "rsi" in caplog.text.lower()


def test_sell_branch(caplog):
    caplog.set_level(logging.INFO)
    prices = [30, 32, 31, 35, 40, 42, 41, 43, 47, 50, 55, 60, 65, 70, 75, 80, 90, 100]
    result = rsi_signal(make_bars(prices), period=14)
    assert result == "SELL"
    assert "rsi" in caplog.text.lower()


def test_hold_branch(caplog):
    caplog.set_level(logging.DEBUG)
    prices = [50, 52, 48, 51, 49, 50, 51, 49, 50, 52, 48, 51, 49, 50, 51, 49, 50, 52, 48, 51]
    result = rsi_signal(make_bars(prices), period=14)
    assert result == "HOLD"
    assert "inside 30-70" in caplog.text.lower()


# ----------------------------
# Loss=0 Fallbacks
# ----------------------------
def test_loss_zero_positive_gain(caplog):
    caplog.set_level(logging.WARNING)
    prices = list(range(100, 130))  # only gains, no losses
    result = rsi_signal(make_bars(prices), period=14)
    assert result == "SELL"
    assert "loss=0" in caplog.text.lower()


def test_loss_zero_non_positive_gain(caplog):
    caplog.set_level(logging.WARNING)
    prices = [100] * 30  # flat prices → no gain, no loss
    result = rsi_signal(make_bars(prices), period=14)
    assert result == "BUY"
    assert "loss=0" in caplog.text.lower()


# ----------------------------
# Exception Handling
# ----------------------------
def test_exception_branch(monkeypatch, caplog):
    caplog.set_level(logging.ERROR)
    monkeypatch.setattr(
        "pandas.DataFrame", lambda *_a, **_k: (_ for _ in ()).throw(Exception("boom"))
    )
    bars = make_bars(range(20))
    result = rsi_signal(bars, period=14)
    assert result == "HOLD"
    assert "failed" in caplog.text.lower()
