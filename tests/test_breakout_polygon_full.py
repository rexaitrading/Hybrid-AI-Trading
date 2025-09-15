"""
Unit Tests: Breakout Polygon (Hybrid AI Quant Pro v7.6 – Final 100% Coverage with Standardized Logs)
---------------------------------------------------------------------------------------------------
Covers ALL branches:
- API key missing
- API error branch
- Unexpected API format
- API returns empty list
- Not enough bars
- Incomplete data
- NaN values
- BUY / SELL / HOLD decisions
- Inner parse exceptions
- Outermost structural crashes
"""

import pytest
import logging
import builtins
from unittest.mock import patch, MagicMock
from hybrid_ai_trading.signals.breakout_polygon import breakout_signal_polygon, get_polygon_bars


# ===========================
# API Error & Key Handling
# ===========================
def test_polygon_key_missing(monkeypatch, caplog):
    monkeypatch.setenv("POLYGON_KEY", "")
    caplog.set_level(logging.WARNING)
    result = get_polygon_bars("AAPL", limit=3)
    assert result == []
    assert "key" in caplog.text.lower()


@patch("hybrid_ai_trading.signals.breakout_polygon.requests.get")
def test_polygon_api_error(mock_get, caplog, monkeypatch):
    monkeypatch.setenv("POLYGON_KEY", "fake")
    mock_get.side_effect = Exception("network down")
    caplog.set_level(logging.ERROR)
    result = get_polygon_bars("AAPL", limit=3)
    assert result == []
    assert "api error" in caplog.text.lower()


@patch("hybrid_ai_trading.signals.breakout_polygon.requests.get")
def test_polygon_unexpected_api_format(mock_get, monkeypatch, caplog):
    caplog.set_level(logging.ERROR)
    monkeypatch.setenv("POLYGON_KEY", "fake")
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"results": {"c": 100, "h": 105, "l": 99}},  # dict not list
    )
    result = get_polygon_bars("AAPL", limit=3)
    assert result == []
    assert "unexpected" in caplog.text.lower()


def test_polygon_api_returns_empty_list(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)

    def fake_get(*a, **k):
        class Resp:
            def json(self): return {"results": []}
            def raise_for_status(self): return None
        return Resp()

    monkeypatch.setenv("POLYGON_KEY", "fake")
    monkeypatch.setattr("hybrid_ai_trading.signals.breakout_polygon.requests.get", fake_get)
    results = get_polygon_bars("AAPL", limit=3)
    assert results == []


# ===========================
# Data Validation
# ===========================
def test_not_enough_bars(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(
        "hybrid_ai_trading.signals.breakout_polygon.get_polygon_bars",
        lambda t, limit=3: [{"c": 100, "h": 101, "l": 99}],
    )
    result = breakout_signal_polygon("AAPL")
    assert result == "HOLD"
    assert "not enough bars" in caplog.text.lower()


def test_incomplete_data(monkeypatch, caplog):
    caplog.set_level(logging.WARNING)
    monkeypatch.setattr(
        "hybrid_ai_trading.signals.breakout_polygon.get_polygon_bars",
        lambda t, limit=3: [
            {"c": 100, "h": 101},      # missing "l"
            {"c": 102, "h": 103, "l": 98},
            {"c": 104},                # missing both
        ],
    )
    result = breakout_signal_polygon("AAPL")
    assert result == "HOLD"
    assert "incomplete" in caplog.text.lower()


def test_polygon_nan_branch(monkeypatch, caplog):
    caplog.set_level(logging.WARNING)
    bars = [
        {"c": 100, "h": 105, "l": 99},
        {"c": 101, "h": 106, "l": 97},
        {"c": float("nan"), "h": 107, "l": 98},  # NaN close
    ]
    monkeypatch.setattr(
        "hybrid_ai_trading.signals.breakout_polygon.get_polygon_bars",
        lambda *a, **k: bars,
    )
    result = breakout_signal_polygon("AAPL")
    assert result == "HOLD"
    assert "nan" in caplog.text.lower()


# ===========================
# Trading Decisions
# ===========================
def test_buy_signal(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    bars = [
        {"c": 100, "h": 101, "l": 99},
        {"c": 102, "h": 103, "l": 97},
        {"c": 110, "h": 111, "l": 109},  # breakout
    ]
    monkeypatch.setattr("hybrid_ai_trading.signals.breakout_polygon.get_polygon_bars", lambda *a, **k: bars)
    result = breakout_signal_polygon("AAPL")
    assert result == "BUY"
    assert "buy" in caplog.text.lower()


def test_sell_signal(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    bars = [
        {"c": 100, "h": 105, "l": 100},
        {"c": 99, "h": 104, "l": 98},
        {"c": 90, "h": 95, "l": 89},  # breakdown
    ]
    monkeypatch.setattr("hybrid_ai_trading.signals.breakout_polygon.get_polygon_bars", lambda *a, **k: bars)
    result = breakout_signal_polygon("AAPL")
    assert result == "SELL"
    assert "sell" in caplog.text.lower()


def test_hold_signal(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    bars = [
        {"c": 100, "h": 105, "l": 99},
        {"c": 102, "h": 106, "l": 97},
        {"c": 103, "h": 107, "l": 98},  # inside range
    ]
    monkeypatch.setattr("hybrid_ai_trading.signals.breakout_polygon.get_polygon_bars", lambda *a, **k: bars)
    result = breakout_signal_polygon("AAPL")
    assert result == "HOLD"
    assert "hold" in caplog.text.lower()


# ===========================
# Exception Handling
# ===========================
@patch("hybrid_ai_trading.signals.breakout_polygon.get_polygon_bars", side_effect=Exception("boom"))
def test_inner_exception_branch(mock_bars, caplog):
    caplog.set_level(logging.ERROR)
    result = breakout_signal_polygon("AAPL")
    assert result == "HOLD"
    assert "failed" in caplog.text.lower()


def test_outermost_handler_with_bad_float(monkeypatch, caplog):
    caplog.set_level(logging.ERROR)
    monkeypatch.setattr(
        "hybrid_ai_trading.signals.breakout_polygon.get_polygon_bars",
        lambda *a, **k: [{"c": 100, "h": 105, "l": 95}] * 3,
    )
    monkeypatch.setattr(builtins, "float", lambda x: (_ for _ in ()).throw(RuntimeError("boom")))
    result = breakout_signal_polygon("AAPL")
    assert result == "HOLD"
    assert "failed" in caplog.text.lower()


def test_outermost_handler_with_badvalue(monkeypatch, caplog):
    caplog.set_level(logging.ERROR)

    class BadValue:
        def __float__(self):
            raise RuntimeError("bad float")

    monkeypatch.setattr(
        "hybrid_ai_trading.signals.breakout_polygon.get_polygon_bars",
        lambda *a, **k: [{"c": BadValue(), "h": 105, "l": 95}] * 3,
    )
    result = breakout_signal_polygon("AAPL")
    assert result == "HOLD"
    assert "failed" in caplog.text.lower()


def test_outermost_handler_during_isnan(monkeypatch, caplog):
    caplog.set_level(logging.ERROR)

    class Exploding:
        def __float__(self): return 100.0

    bars = [
        {"c": Exploding(), "h": 105, "l": 95},
        {"c": Exploding(), "h": 106, "l": 96},
        {"c": Exploding(), "h": 107, "l": 97},
    ]
    monkeypatch.setattr("hybrid_ai_trading.signals.breakout_polygon.get_polygon_bars", lambda *a, **k: bars)
    monkeypatch.setattr("math.isnan", lambda v: (_ for _ in ()).throw(RuntimeError("boom")))
    result = breakout_signal_polygon("AAPL")
    assert result == "HOLD"
    assert "failed" in caplog.text.lower()
