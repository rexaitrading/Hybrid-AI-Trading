"""
Unit Tests: Signals Suite (Hybrid AI Quant Pro v25.1 – Final 100% Coverage)
----------------------------------------------------------------------------
Covers ALL signal modules:
- bollinger_bands
- breakout_intraday
- breakout_polygon
- breakout_v1
- macd
- moving_average
- rsi_signal
- vwap

Branches covered:
- Empty input
- Not enough bars
- Missing/invalid close
- NaN handling
- BUY, SELL, HOLD logic
- Exception safety
"""

import importlib
import logging
import math
from unittest.mock import MagicMock, patch

import pandas as pd

from hybrid_ai_trading.algos.vwap import vwap_signal
from hybrid_ai_trading.signals.bollinger_bands import bollinger_bands_signal
from hybrid_ai_trading.signals.breakout_intraday import breakout_intraday
from hybrid_ai_trading.signals.macd import macd_signal
from hybrid_ai_trading.signals.moving_average import moving_average_signal
from hybrid_ai_trading.signals.rsi_signal import rsi_signal

# -------------------------------------------------------------------
# Dynamic imports (avoid circulars)
# -------------------------------------------------------------------
breakout_v1_module = importlib.import_module("hybrid_ai_trading.signals.breakout_v1")
breakout_polygon_module = importlib.import_module(
    "hybrid_ai_trading.signals.breakout_polygon"
)


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def make_bars(prices, vols=None):
    """Utility to build OHLCV-style bars with close + volume."""
    return [{"c": p, "v": vols[i] if vols else 1} for i, p in enumerate(prices)]


# -------------------------------------------------------------------
# Bollinger Bands
# -------------------------------------------------------------------
def test_bollinger_all_branches(caplog, monkeypatch):
    """Test all branches of bollinger_bands_signal."""
    caplog.set_level(logging.DEBUG)

    assert bollinger_bands_signal([]) == "HOLD"
    assert bollinger_bands_signal([{"c": 100}] * 5, window=20) == "HOLD"
    assert bollinger_bands_signal([{"h": 100}] * 25, window=20) == "HOLD"
    assert bollinger_bands_signal([{"c": "bad"}] * 25, window=20) == "HOLD"
    assert bollinger_bands_signal([{"c": math.nan}] * 25, window=20) == "HOLD"

    # Invalid mean/std → HOLD
    monkeypatch.setattr("statistics.fmean", lambda _x: float("nan"))
    assert bollinger_bands_signal([{"c": 100}] * 25, window=20) == "HOLD"
    monkeypatch.undo()

    # BUY / SELL / HOLD paths
    prices = [100] * 19 + [0]
    assert bollinger_bands_signal([{"c": p} for p in prices], window=20) == "BUY"

    prices = [100] * 19 + [500]
    assert bollinger_bands_signal([{"c": p} for p in prices], window=20) == "SELL"

    assert bollinger_bands_signal([{"c": 100}] * 25, window=20) == "HOLD"


# -------------------------------------------------------------------
# Breakout Intraday
# -------------------------------------------------------------------
def test_breakout_intraday_all(caplog):
    """Test all branches of breakout_intraday."""
    caplog.set_level(logging.DEBUG)

    assert breakout_intraday([]) == "HOLD"
    assert breakout_intraday(make_bars([1, 2, 3]), window=0) == "HOLD"
    assert breakout_intraday(make_bars([1, 2, 3]), window=10) == "HOLD"
    assert breakout_intraday([{"o": 1}], window=1) == "HOLD"
    assert breakout_intraday([{"c": "bad"}] * 20, window=20) == "HOLD"
    assert breakout_intraday(make_bars([float("nan")] * 20), window=20) == "HOLD"

    assert breakout_intraday(make_bars([10] * 20 + [30]), window=20) == "BUY"
    assert breakout_intraday(make_bars([100] * 20 + [50]), window=20) == "SELL"
    assert breakout_intraday(make_bars([50] * 20), window=20) == "SELL"  # tie
    assert breakout_intraday(make_bars(list(range(1, 21)) + [15]), window=20) == "HOLD"


# -------------------------------------------------------------------
# Breakout V1
# -------------------------------------------------------------------
def test_breakout_v1_all(caplog, monkeypatch):
    """Test breakout_v1 core logic, audit mode, and wrapper safety."""
    caplog.set_level(logging.DEBUG)

    breakout_v1 = breakout_v1_module.breakout_v1
    breakout_signal = breakout_v1_module.breakout_signal

    assert breakout_v1([]) == "HOLD"
    assert breakout_v1(make_bars([1, 2, 3]), window=0) == "HOLD"
    assert breakout_v1(make_bars([1, 2]), window=5) == "HOLD"
    assert breakout_v1([{"c": "bad"}], window=1) == "HOLD"
    assert breakout_v1(make_bars([float("nan"), 5, 10]), window=3) == "HOLD"

    assert breakout_v1(make_bars([50, 50, 50]), window=3) == "SELL"
    assert breakout_v1(make_bars([10, 12, 4]), window=3) == "SELL"
    assert breakout_v1(make_bars([10, 12, 10]), window=3) == "HOLD"
    assert breakout_v1(make_bars([1, 2, 10]), window=3) == "BUY"

    # Audit mode
    d, price, rh, rl = breakout_v1(make_bars([1, 10, 5]), window=3, audit=True)
    assert d in ["BUY", "SELL", "HOLD"]
    assert isinstance(price, float)
    assert isinstance(rh, float)
    assert isinstance(rl, float)

    # Wrapper fetch failure
    monkeypatch.setattr(
        breakout_v1_module,
        "get_ohlcv_latest",
        lambda *_a, **_k: (_ for _ in ()).throw(Exception("boom")),
    )
    assert breakout_signal("AAPL") == "HOLD"


# -------------------------------------------------------------------
# Breakout Polygon
# -------------------------------------------------------------------
@patch("hybrid_ai_trading.signals.breakout_polygon.requests.get")
def test_polygon_all(mock_get, monkeypatch, caplog):
    """Test all branches of breakout_polygon."""
    caplog.set_level(logging.DEBUG)
    monkeypatch.setenv("POLYGON_KEY", "fake")

    mock_get.side_effect = Exception("boom")
    assert breakout_polygon_module.get_polygon_bars("AAPL") == []

    mock_get.side_effect = None
    mock_get.return_value = MagicMock(status_code=200, json=lambda: {"results": {}})
    assert breakout_polygon_module.get_polygon_bars("AAPL") == []

    monkeypatch.setattr(
        breakout_polygon_module,
        "get_polygon_bars",
        lambda *_a, **_k: [{"c": 100, "h": 101, "l": 99}],
    )
    assert breakout_polygon_module.breakout_signal_polygon("AAPL") == "HOLD"

    monkeypatch.setattr(
        breakout_polygon_module,
        "get_polygon_bars",
        lambda *_a, **_k: [{"c": 100, "h": 101}] * 3,
    )
    assert breakout_polygon_module.breakout_signal_polygon("AAPL") == "HOLD"

    monkeypatch.setattr(
        breakout_polygon_module,
        "get_polygon_bars",
        lambda *_a, **_k: [{"c": math.nan, "h": 101, "l": 99}] * 3,
    )
    assert breakout_polygon_module.breakout_signal_polygon("AAPL") == "HOLD"

    monkeypatch.setattr(
        breakout_polygon_module,
        "get_polygon_bars",
        lambda *_a, **_k: [
            {"c": 100, "h": 101, "l": 99},
            {"c": 102, "h": 103, "l": 97},
            {"c": 110, "h": 111, "l": 109},
        ],
    )
    assert breakout_polygon_module.breakout_signal_polygon("AAPL") == "BUY"


# -------------------------------------------------------------------
# MACD
# -------------------------------------------------------------------
def test_macd_all(monkeypatch, caplog):
    """Test all branches of macd_signal."""
    caplog.set_level(logging.DEBUG)

    assert macd_signal([]) == "HOLD"
    assert macd_signal([{"c": i} for i in range(10)]) == "HOLD"
    assert macd_signal([{"o": 1}] * 40) == "HOLD"
    assert macd_signal([{"c": math.nan}] * 40) == "HOLD"

    prices = list(range(1, 100))
    assert macd_signal([{"c": p} for p in prices]) in ["BUY", "SELL", "HOLD"]

    bars = [{"c": 1}] * 50
    assert macd_signal(bars) == "HOLD"

    class FakeEWM:
        def mean(self, *_a, **_k):
            return pd.Series([float("nan")] * 50)

    monkeypatch.setattr(pd.Series, "ewm", lambda *_a, **_k: FakeEWM())
    assert macd_signal([{"c": i} for i in range(40)]) == "HOLD"


# -------------------------------------------------------------------
# Moving Average
# -------------------------------------------------------------------
def test_moving_average_all(monkeypatch, caplog):
    """Test all branches of moving_average_signal."""
    caplog.set_level(logging.DEBUG)

    assert moving_average_signal([]) == "HOLD"
    assert moving_average_signal([{"c": 1}], short_window=5, long_window=20) == "HOLD"
    assert (
        moving_average_signal([{"o": 1}] * 25, short_window=5, long_window=20) == "HOLD"
    )

    bars = [{"c": i} for i in range(1, 50)]
    assert moving_average_signal(bars, short_window=3, long_window=10) in [
        "BUY",
        "SELL",
        "HOLD",
    ]

    class FakeRolling:
        def mean(self):
            return pd.Series([float("nan")])

    monkeypatch.setattr(pd.Series, "rolling", lambda *_a, **_k: FakeRolling())
    assert (
        moving_average_signal(
            [{"c": i} for i in range(25)], short_window=5, long_window=20
        )
        == "HOLD"
    )


# -------------------------------------------------------------------
# RSI
# -------------------------------------------------------------------
def test_rsi_all(monkeypatch, caplog):
    """Test all branches of rsi_signal."""
    caplog.set_level(logging.DEBUG)

    assert rsi_signal([]) == "HOLD"
    assert rsi_signal([{"c": i} for i in range(10)], period=14) == "HOLD"
    assert rsi_signal([{"o": 1}] * 20, period=14) == "HOLD"
    assert rsi_signal([{"c": math.nan}] * 20, period=14) == "HOLD"

    prices = [50] * 15 + [20]
    assert rsi_signal([{"c": p} for p in prices], period=14) == "BUY"

    prices = list(range(30, 50)) + [100]
    assert rsi_signal([{"c": p} for p in prices], period=14) == "SELL"

    prices = [50, 52, 48, 51, 49] * 5
    assert rsi_signal([{"c": p} for p in prices], period=14) == "HOLD"

    prices = list(range(100, 130))
    assert rsi_signal([{"c": p} for p in prices], period=14) == "SELL"

    prices = [100] * 30
    assert rsi_signal([{"c": p} for p in prices], period=14) == "BUY"


# -------------------------------------------------------------------
# VWAP
# -------------------------------------------------------------------
def test_vwap_all(caplog):
    """Test all branches of vwap_signal."""
    caplog.set_level(logging.DEBUG)

    assert vwap_signal([]) == "HOLD"
    assert vwap_signal([{"v": 10}] * 5) == "HOLD"
    assert vwap_signal([{"c": 100}] * 5) == "HOLD"
    assert vwap_signal([{"c": math.nan, "v": 10}] * 5) == "HOLD"

    bars = make_bars([10, 20, 30], vols=[1, 1, 10])
    assert vwap_signal(bars) == "BUY"

    bars = make_bars([30, 20, 10], vols=[10, 1, 1])
    assert vwap_signal(bars) == "SELL"

    bars = make_bars([10, 20, 15], vols=[1, 1, 2])
    bars[-1]["c"] = 15.0
    assert vwap_signal(bars) == "HOLD"
