import pytest
from unittest.mock import patch
from src.signals.breakout_v1 import breakout_signal


@patch("src.signals.breakout_v1.get_ohlcv_latest")
def test_breakout_buy(mock_get):
    # Last close > previous highs → BUY
    mock_get.return_value = [
        {"price_close": 100, "price_high": 100, "price_low": 95},
        {"price_close": 102, "price_high": 102, "price_low": 96},
        {"price_close": 105, "price_high": 103, "price_low": 97},
    ]
    assert breakout_signal("BTC/USD") == "BUY"


@patch("src.signals.breakout_v1.get_ohlcv_latest")
def test_breakout_sell(mock_get):
    # Last close < previous lows → SELL
    mock_get.return_value = [
        {"price_close": 100, "price_high": 105, "price_low": 99},
        {"price_close": 98, "price_high": 102, "price_low": 97},
        {"price_close": 95, "price_high": 100, "price_low": 94},
    ]
    assert breakout_signal("BTC/USD") == "SELL"


@patch("src.signals.breakout_v1.get_ohlcv_latest")
def test_breakout_hold(mock_get):
    # Last close inside the range → HOLD
    mock_get.return_value = [
        {"price_close": 100, "price_high": 105, "price_low": 95},
        {"price_close": 102, "price_high": 106, "price_low": 97},
        {"price_close": 104, "price_high": 106, "price_low": 98},
    ]
    assert breakout_signal("BTC/USD") == "HOLD"


@patch("src.signals.breakout_v1.get_ohlcv_latest")
def test_breakout_not_enough_bars(mock_get):
    # Fewer than 3 bars → HOLD
    mock_get.return_value = [
        {"price_close": 100, "price_high": 100, "price_low": 95},
    ]
    assert breakout_signal("BTC/USD") == "HOLD"
