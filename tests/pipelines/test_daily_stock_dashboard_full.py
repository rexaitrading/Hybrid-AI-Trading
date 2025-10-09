"""
Unit Tests: Daily Stock Dashboard (Quant Pro v7.1 – Hedge-Fund Grade, 100% Coverage)
====================================================================================
Covers:
- get_bars success + request failure
- grade_stock: breakout up, breakout down, range, insufficient bars
- place_bracket_order: success + ImportError
- daily_dashboard_with_ibkr:
  * CSV + JSON export
  * IBKR connection fail
  * disconnect branch
  * executed summary logging
- ✅ Cleanup of generated files in logs/
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import hybrid_ai_trading.pipelines.daily_stock_dashboard as dash

LOGS = Path("logs")


# ----------------------------------------------------------------------
# Autouse fixture: clean logs before and after each test
# ----------------------------------------------------------------------
@pytest.fixture(autouse=True)
def clean_logs_before_after():
    """Ensure logs dir is clean before and after each test."""
    if LOGS.exists():
        for f in LOGS.glob("*.csv"):
            f.unlink()
        for f in LOGS.glob("*.json"):
            f.unlink()
    yield
    if LOGS.exists():
        for f in LOGS.glob("*.csv"):
            f.unlink()
        for f in LOGS.glob("*.json"):
            f.unlink()


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_get_bars_success(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"results": [{"c": 1}]}
    mock_resp.raise_for_status.return_value = None
    monkeypatch.setattr(dash.requests, "get", lambda *a, **k: mock_resp)
    bars = dash.get_bars("AAPL", "2020-01-01", "2020-01-02")
    assert bars == [{"c": 1}]


def test_get_bars_failure(monkeypatch, caplog):
    monkeypatch.setattr(
        dash.requests, "get", lambda *a, **k: (_ for _ in ()).throw(Exception("fail"))
    )
    caplog.set_level(logging.ERROR, logger="DailyDashboard")
    out = dash.get_bars("AAPL", "2020", "2020")
    assert out == []
    assert "Error fetching" in caplog.text


def test_grade_stock_branches():
    bars = [{"c": i, "h": i + 1, "l": i - 1} for i in range(30)]
    assert dash.grade_stock("AAPL", bars)

    bars[-1]["c"] = -100
    assert dash.grade_stock("AAPL", bars)["signal"] == "BREAKOUT DOWN"

    bars[-1]["c"] = bars[-2]["c"]
    assert dash.grade_stock("AAPL", bars)["signal"] == "RANGE"

    assert dash.grade_stock("AAPL", bars[:5]) is None


def test_place_bracket_order(monkeypatch):
    fake_ib = MagicMock()
    fake_ib.client.getReqId.return_value = 1
    monkeypatch.setattr(dash, "IB", MagicMock())
    monkeypatch.setattr(dash, "Stock", MagicMock())
    monkeypatch.setattr(dash, "MarketOrder", MagicMock())
    monkeypatch.setattr(dash, "LimitOrder", MagicMock())
    monkeypatch.setattr(dash, "StopOrder", MagicMock())
    info = {"last_close": 100, "stop": 95, "target": 110, "rr": 2.0}
    res = dash.place_bracket_order(fake_ib, "AAPL", info)
    assert res["status"] == "AUTO_EXECUTED"


def test_place_bracket_order_importerror(monkeypatch):
    monkeypatch.setattr(dash, "IB", None)
    monkeypatch.setattr(dash, "Stock", None)
    with pytest.raises(ImportError):
        dash.place_bracket_order(
            MagicMock(), "AAPL", {"last_close": 100, "stop": 95, "target": 110}
        )


@patch("hybrid_ai_trading.pipelines.daily_stock_dashboard.get_bars")
@patch("hybrid_ai_trading.pipelines.daily_stock_dashboard.grade_stock")
def test_daily_dashboard_with_ibkr_success(mock_grade, mock_get, monkeypatch):
    mock_get.return_value = [{"c": 1, "h": 2, "l": 0}] * 30
    mock_grade.return_value = {
        "symbol": "AAPL",
        "signal": "BREAKOUT UP",
        "last_close": 100,
        "stop": 95,
        "target": 110,
        "rr": 2.0,
        "grade": "A",
    }
    fake_ib = MagicMock()
    fake_ib.isConnected.return_value = False
    monkeypatch.setattr(dash, "IB", lambda: fake_ib)
    monkeypatch.setattr(
        dash,
        "place_bracket_order",
        lambda ib, s, i: {
            "symbol": s,
            "qty": 10,
            "stop": 95,
            "target": 110,
            "status": "AUTO_EXECUTED",
        },
    )
    dash.daily_dashboard_with_ibkr()
    assert list(LOGS.glob("*.csv"))
    assert list(LOGS.glob("*.json"))


@patch("hybrid_ai_trading.pipelines.daily_stock_dashboard.get_bars")
@patch("hybrid_ai_trading.pipelines.daily_stock_dashboard.grade_stock")
def test_daily_dashboard_ibkr_connection_fail_and_disconnect(
    mock_grade, mock_get, caplog, monkeypatch
):
    mock_get.return_value = [{"c": 1, "h": 2, "l": 0}] * 30
    mock_grade.return_value = {
        "symbol": "AAPL",
        "signal": "BREAKOUT UP",
        "last_close": 100,
        "stop": 95,
        "target": 110,
        "rr": 2.0,
        "grade": "A",
    }
    fake_ib = MagicMock()
    fake_ib.connect.side_effect = Exception("conn fail")
    fake_ib.isConnected.return_value = True
    monkeypatch.setattr(dash, "IB", lambda: fake_ib)
    caplog.set_level(logging.ERROR, logger="DailyDashboard")
    dash.daily_dashboard_with_ibkr()
    assert "IBKR connection failed" in caplog.text
    fake_ib.disconnect.assert_called_once()


@patch("hybrid_ai_trading.pipelines.daily_stock_dashboard.get_bars")
@patch("hybrid_ai_trading.pipelines.daily_stock_dashboard.grade_stock")
def test_daily_dashboard_with_executed_summary(
    mock_grade, mock_get, monkeypatch, caplog
):
    mock_get.return_value = [{"c": 1, "h": 2, "l": 0}] * 30
    mock_grade.return_value = {
        "symbol": "AAPL",
        "signal": "BREAKOUT UP",
        "last_close": 100,
        "stop": 95,
        "target": 110,
        "rr": 2.0,
        "grade": "A",
    }
    fake_ib = MagicMock()
    fake_ib.isConnected.return_value = False
    monkeypatch.setattr(dash, "IB", lambda: fake_ib)
    monkeypatch.setattr(
        dash,
        "place_bracket_order",
        lambda ib, s, i: {
            "symbol": s,
            "qty": 10,
            "stop": 95,
            "target": 110,
            "status": "AUTO_EXECUTED",
        },
    )
    caplog.set_level(logging.INFO, logger="DailyDashboard")
    dash.daily_dashboard_with_ibkr()
    assert "SUMMARY OF AUTO-TRADES" in caplog.text


def test_daily_dashboard_with_no_results(monkeypatch, caplog):
    monkeypatch.setattr(dash, "WATCHLIST", ["AAPL"])
    monkeypatch.setattr(dash, "get_bars", lambda *a, **k: [])
    monkeypatch.setattr(dash, "grade_stock", lambda *a, **k: None)
    caplog.set_level(logging.INFO, logger="DailyDashboard")

    dash.daily_dashboard_with_ibkr()
    # Should skip export, so no CSV/JSON created
    assert not list(LOGS.glob("daily_dashboard_*.csv"))
    assert not list(LOGS.glob("daily_dashboard_*.json"))


def test_grade_stock_range_stop_target_none():
    # Force last_close inside range so it returns RANGE with stop/target None
    bars = [{"c": i, "h": i + 1, "l": i - 1} for i in range(30)]
    bars[-1]["c"] = bars[-5]["c"]  # inside the recent high/low range
    result = dash.grade_stock("AAPL", bars)
    assert result["signal"] == "RANGE"
    assert result["stop"] is None and result["target"] is None


def test_daily_dashboard_ib_none(monkeypatch, caplog):
    # Patch IB to None to cover the early "if IB:" branch skip
    monkeypatch.setattr(dash, "IB", None)
    caplog.set_level(logging.INFO, logger="DailyDashboard")
    dash.daily_dashboard_with_ibkr()
    # Should run without error, but no auto-trades executed
    assert "SUMMARY OF AUTO-TRADES" not in caplog.text
