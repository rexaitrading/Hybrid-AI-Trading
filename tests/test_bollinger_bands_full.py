"""
Unit Tests: Bollinger Bands (Hybrid AI Quant Pro v14.7 – 100% Coverage Stable)
-------------------------------------------------------------------------------
Covers every branch and edge case:
- No bars
- Not enough bars
- Missing 'c'
- Parse failure
- NaN closes
- NaN mean/std
- stdev=0 flat prices → HOLD
- BUY below lower band
- SELL above upper band
- HOLD inside bands
"""

import pytest
import logging
import pandas as pd
from hybrid_ai_trading.signals.bollinger_bands import bollinger_bands_signal


# =====================================================
# Data Validation Branches
# =====================================================

def test_no_bars(caplog):
    caplog.set_level(logging.INFO)
    result = bollinger_bands_signal([], window=20)
    assert result == "HOLD"
    # standardized keyword check
    assert "no bars" in caplog.text.lower()


def test_not_enough_bars(caplog):
    caplog.set_level(logging.INFO)
    bars = [{"c": 100}] * 5
    result = bollinger_bands_signal(bars, window=20)
    assert result == "HOLD"
    assert "not enough bars" in caplog.text.lower()


def test_missing_close_field(caplog):
    caplog.set_level(logging.WARNING)
    bars = [{"h": 100, "l": 95}] * 25
    result = bollinger_bands_signal(bars, window=20)
    assert result == "HOLD"
    assert "missing" in caplog.text.lower()


def test_parse_failure(caplog):
    caplog.set_level(logging.ERROR)
    bars = [{"c": "bad"}] * 25
    result = bollinger_bands_signal(bars, window=20)
    assert result == "HOLD"
    assert "parse" in caplog.text.lower()


def test_nan_closes(caplog):
    caplog.set_level(logging.WARNING)
    bars = [{"c": float("nan")}] * 25
    result = bollinger_bands_signal(bars, window=20)
    assert result == "HOLD"
    assert "nan" in caplog.text.lower()


def test_nan_mean_std(monkeypatch, caplog):
    caplog.set_level(logging.WARNING)
    bars = [{"c": 100.0}] * 25

    monkeypatch.setattr("statistics.fmean", lambda x: float("nan"))
    result = bollinger_bands_signal(bars, window=20)
    assert result == "HOLD"
    assert "invalid" in caplog.text.lower()


# =====================================================
# Decision Logic
# =====================================================

def test_buy_signal(caplog):
    caplog.set_level(logging.INFO)
    bars = [{"c": 100 + i} for i in range(19)]
    bars.append({"c": 50})  # below lower band
    result = bollinger_bands_signal(bars, window=20)
    assert result == "BUY"
    assert "buy" in caplog.text.lower()


def test_sell_signal(caplog):
    caplog.set_level(logging.INFO)
    bars = [{"c": 100 + i} for i in range(19)]
    bars.append({"c": 200})  # above upper band
    result = bollinger_bands_signal(bars, window=20)
    assert result == "SELL"
    assert "sell" in caplog.text.lower()


def test_hold_flat_prices(caplog):
    caplog.set_level(logging.DEBUG)
    bars = [{"c": 100}] * 25  # stdev=0
    result = bollinger_bands_signal(bars, window=20)
    assert result == "HOLD"
    assert "hold" in caplog.text.lower()


def test_hold_inside_range(caplog):
    caplog.set_level(logging.DEBUG)
    prices = [100 + (i % 2) for i in range(25)]
    bars = [{"c": p} for p in prices]
    result = bollinger_bands_signal(bars, window=20)
    assert result == "HOLD"
    assert "hold" in caplog.text.lower()
