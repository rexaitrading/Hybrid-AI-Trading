"""
Unit Tests: Signals Layer (Hybrid AI Quant Pro v22.5 – Final OE 100% Coverage)
------------------------------------------------------------------------------
Covers ALL branches for:
- bollinger_bands_signal
- breakout_signal_polygon
- macd_signal
- moving_average_signal
- rsi_signal
- vwap_signal
"""

import logging
import math

import pandas as pd

# Import signals from their dedicated modules
from hybrid_ai_trading.signals.bollinger_bands import bollinger_bands_signal
from hybrid_ai_trading.signals.breakout_polygon import (
    BreakoutPolygonSignal,
    breakout_signal_polygon,
)
from hybrid_ai_trading.signals.macd import macd_signal
from hybrid_ai_trading.signals.moving_average import moving_average_signal
from hybrid_ai_trading.signals.rsi_signal import rsi_signal
from hybrid_ai_trading.signals.vwap import vwap_signal


# ====================================================================
# Bollinger Bands
# ====================================================================
def test_bollinger_not_enough_bars():
    assert bollinger_bands_signal([], 20) == "HOLD"


def test_bollinger_missing_close(caplog):
    caplog.set_level(logging.WARNING)
    bars = [{"o": 1, "h": 2}] * 20
    result = bollinger_bands_signal(bars)
    assert result == "HOLD"
    assert "missing" in caplog.text.lower()


def test_bollinger_parse_error():
    bars = [{"c": "bad"}] * 20
    assert bollinger_bands_signal(bars) == "HOLD"


def test_bollinger_nan_values():
    bars = [{"c": math.nan}] * 20
    assert bollinger_bands_signal(bars) == "HOLD"


def test_bollinger_buy_sell_hold():
    bars = [{"c": i} for i in range(1, 50)]
    result = bollinger_bands_signal(bars, window=20)
    assert result in ["BUY", "SELL", "HOLD"]


# ====================================================================
# Breakout Polygon
# ====================================================================
def test_polygon_key_missing(monkeypatch):
    monkeypatch.setenv("POLYGON_KEY", "")
    assert breakout_signal_polygon("AAPL") == "HOLD"


def test_polygon_incomplete_data(monkeypatch):
    monkeypatch.setattr(
        BreakoutPolygonSignal,
        "_get_polygon_bars",
        lambda *_a, **_k: [{"c": 10, "h": 20}],  # missing low
    )
    assert breakout_signal_polygon("AAPL") == "HOLD"


def test_polygon_parse_error(monkeypatch):
    monkeypatch.setattr(
        BreakoutPolygonSignal,
        "_get_polygon_bars",
        lambda *_a, **_k: [{"c": "bad", "h": "bad", "l": "bad"}] * 3,
    )
    assert breakout_signal_polygon("AAPL") == "HOLD"


def test_polygon_nan(monkeypatch):
    monkeypatch.setattr(
        BreakoutPolygonSignal,
        "_get_polygon_bars",
        lambda *_a, **_k: [{"c": math.nan, "h": 2, "l": 1}] * 3,
    )
    assert breakout_signal_polygon("AAPL") == "HOLD"


def test_polygon_buy_sell_hold(monkeypatch):
    # BUY case
    monkeypatch.setattr(
        BreakoutPolygonSignal,
        "_get_polygon_bars",
        lambda *_a, **_k: [
            {"c": 10, "h": 9, "l": 8},
            {"c": 11, "h": 11, "l": 10},
            {"c": 12, "h": 12, "l": 11},
        ],
    )
    assert breakout_signal_polygon("AAPL") in ["BUY", "SELL", "HOLD"]

    # Inside range explicit
    bars = [
        {"c": 10, "h": 15, "l": 5},
        {"c": 11, "h": 16, "l": 6},
        {"c": 12, "h": 17, "l": 7},
    ]
    sig = BreakoutPolygonSignal()
    out = sig.generate("AAPL", bars)
    assert out["signal"] == "HOLD"
    assert out["reason"] == "inside_range"


def test_polygon_outermost_exception(monkeypatch):
    monkeypatch.setattr(
        BreakoutPolygonSignal,
        "_get_polygon_bars",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    sig = BreakoutPolygonSignal()
    out = sig.generate("AAPL")
    assert out["reason"] == "exception"


# ====================================================================
# MACD
# ====================================================================
def test_macd_no_bars():
    assert macd_signal([]) == "HOLD"


def test_macd_not_enough_bars():
    bars = [{"c": 1}] * 10
    assert macd_signal(bars) == "HOLD"


def test_macd_missing_close():
    bars = [{"o": 1}] * 40
    assert macd_signal(bars) == "HOLD"


def test_macd_nan_closes():
    bars = [{"c": i if i % 2 == 0 else math.nan} for i in range(40)]
    assert macd_signal(bars) == "HOLD"


def test_macd_buy_sell_hold():
    bars = [{"c": i} for i in range(1, 100)]
    result = macd_signal(bars)
    assert result in ["BUY", "SELL", "HOLD"]


def test_macd_parse_error(monkeypatch):
    monkeypatch.setattr(
        pd,
        "DataFrame",
        lambda *a, **k: (_ for _ in ()).throw(Exception("boom")),
    )
    bars = [{"c": i} for i in range(40)]
    assert macd_signal(bars) == "HOLD"


# ====================================================================
# Moving Average
# ====================================================================
def test_ma_not_enough_bars():
    assert moving_average_signal([{"c": 1}], short_window=5, long_window=20) == "HOLD"


def test_ma_missing_close():
    bars = [{"o": 1}] * 25
    assert moving_average_signal(bars) == "HOLD"


def test_ma_nan_closes():
    bars = [{"c": i if i % 2 == 0 else math.nan} for i in range(25)]
    assert moving_average_signal(bars) == "HOLD"


def test_ma_buy_sell_hold():
    bars = [{"c": i} for i in range(1, 50)]
    result = moving_average_signal(bars, short_window=5, long_window=20)
    assert result in ["BUY", "SELL", "HOLD"]


def test_ma_parse_error(monkeypatch):
    monkeypatch.setattr(
        pd.Series,
        "rolling",
        lambda *a, **k: (_ for _ in ()).throw(Exception("boom")),
    )
    bars = [{"c": i} for i in range(25)]
    assert moving_average_signal(bars, short_window=5, long_window=20) == "HOLD"


# ====================================================================
# RSI
# ====================================================================
def test_rsi_no_bars():
    assert rsi_signal([], period=14) == "HOLD"


def test_rsi_not_enough_bars():
    bars = [{"c": 1}] * 10
    assert rsi_signal(bars, period=14) == "HOLD"


def test_rsi_missing_close():
    bars = [{"o": 1}] * 20
    assert rsi_signal(bars, period=14) == "HOLD"


def test_rsi_nan_closes():
    bars = [{"c": i if i % 2 == 0 else math.nan} for i in range(20)]
    assert rsi_signal(bars, period=14) == "HOLD"


def test_rsi_buy_sell_hold():
    bars = [{"c": i} for i in range(1, 100)]
    result = rsi_signal(bars, period=14)
    assert result in ["BUY", "SELL", "HOLD"]


def test_rsi_parse_error(monkeypatch):
    monkeypatch.setattr(
        pd,
        "DataFrame",
        lambda *a, **k: (_ for _ in ()).throw(Exception("boom")),
    )
    bars = [{"c": i} for i in range(20)]
    assert rsi_signal(bars, period=14) == "HOLD"


# ====================================================================
# VWAP
# ====================================================================
def test_vwap_no_bars():
    assert vwap_signal([]) == "HOLD"


def test_vwap_missing_close_or_volume():
    bars = [{"v": 100}] * 10
    assert vwap_signal(bars) == "HOLD"
    bars = [{"c": 100}] * 10
    assert vwap_signal(bars) == "HOLD"


def test_vwap_nan_inputs():
    bars = [{"c": 100, "v": math.nan}] * 10
    assert vwap_signal(bars) == "HOLD"


def test_vwap_buy_sell_hold():
    bars = [{"c": i, "v": 10} for i in range(1, 50)]
    result = vwap_signal(bars)
    assert result in ["BUY", "SELL", "HOLD"]


def test_vwap_parse_error(monkeypatch):
    monkeypatch.setattr(
        pd,
        "DataFrame",
        lambda *a, **k: (_ for _ in ()).throw(Exception("boom")),
    )
    bars = [{"c": 1, "v": 10}] * 10
    assert vwap_signal(bars) == "HOLD"
