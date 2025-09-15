# tests/test_backtest_full.py
"""
Full Edge & Branch Coverage: Backtest Pipeline (Hybrid AI Quant Pro v8.7 – 100% Coverage)
========================================================================================
- Tests cover every branch in backtest.py with safe, mockable paths.
"""

import os
import pytest
import yaml
import pandas as pd
import datetime as dt
from copy import deepcopy

from hybrid_ai_trading.pipelines import backtest
from hybrid_ai_trading.pipelines.backtest import IntradayBacktester


# --- Helpers ---
def fake_bars():
    """Return a small deterministic list of bars."""
    return [
        {"t": 1_700_000_000_000, "c": 100},
        {"t": 1_700_000_060_000, "c": 101},
        {"t": 1_700_000_120_000, "c": 102},
        {"t": 1_700_000_180_000, "c": 103},
    ]


def always_buy(_): return "BUY"
def always_sell(_): return "SELL"
def always_hold(_): return "HOLD"
def always_error(_): raise RuntimeError("Bad strategy")


# --- Fixtures ---
@pytest.fixture
def backtester(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "hybrid_ai_trading.pipelines.backtest.get_intraday_bars",
        lambda *a, **k: [deepcopy(b) for _ in range(20) for b in fake_bars()],
    )
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": always_buy})
    bt.reports_dir = tmp_path
    os.makedirs(bt.reports_dir, exist_ok=True)
    return bt


# --- Config Loader ---
def test_load_config_variants(tmp_path, caplog):
    assert backtest.load_config(tmp_path / "nofile.yaml") == {}

    bad = tmp_path / "bad.yaml"
    bad.write_text("::invalid::")
    with caplog.at_level("ERROR"):
        assert backtest.load_config(str(bad)) == {}

    bad_list = tmp_path / "bad_list.yaml"
    bad_list.write_text(yaml.dump(["a", "b"]))
    with caplog.at_level("ERROR"):
        assert backtest.load_config(str(bad_list)) == {}

    bad_key = tmp_path / "bad_key.yaml"
    bad_key.write_text(yaml.dump({123: "val"}))
    with caplog.at_level("ERROR"):
        assert backtest.load_config(str(bad_key)) == {}

    bad_val = tmp_path / "bad_val.yaml"
    bad_val.write_text(yaml.dump({"risk": None}))
    with caplog.at_level("ERROR"):
        assert backtest.load_config(str(bad_val)) == {}

    good = tmp_path / "good.yaml"
    good.write_text(yaml.dump({"risk": {"start_capital": 12345}}))
    cfg = backtest.load_config(str(good))
    assert cfg["risk"]["start_capital"] == 12345


# --- Data Fetcher ---
def test_get_intraday_bars_all_paths(monkeypatch, caplog):
    class GoodResp:
        status_code = 200
        def json(self): return {"results": [1]}
    monkeypatch.setattr("requests.get", lambda *a, **k: GoodResp())
    assert backtest.get_intraday_bars("AAPL", "x", "y", "key") == [1]

    with caplog.at_level("WARNING"):
        assert backtest.get_intraday_bars("AAPL", "x", "y", None) == []

    class BadResp:
        status_code, text = 500, "fail"
        def json(self): return {}
    monkeypatch.setattr("requests.get", lambda *a, **k: BadResp())
    with caplog.at_level("ERROR"):
        assert backtest.get_intraday_bars("AAPL", "x", "y", "key") == []

    class JsonFail:
        status_code = 200
        def json(self): raise Exception("boom")
    monkeypatch.setattr("requests.get", lambda *a, **k: JsonFail())
    with caplog.at_level("ERROR"):
        assert backtest.get_intraday_bars("AAPL", "x", "y", "key") == []

    monkeypatch.setattr(backtest.requests, "get",
                        lambda *a, **k: (_ for _ in ()).throw(Exception("net fail")))
    with caplog.at_level("ERROR"):
        assert backtest.get_intraday_bars("AAPL", "x", "y", "key") == []


# --- IntradayBacktester core ---
@pytest.mark.parametrize("strategy_func", [always_buy, always_sell, always_hold])
def test_run_buy_sell_hold(monkeypatch, tmp_path, strategy_func):
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"s": strategy_func})
    monkeypatch.setattr(
        "hybrid_ai_trading.pipelines.backtest.get_intraday_bars",
        lambda *a, **k: [deepcopy(b) for _ in range(15) for b in fake_bars()],
    )
    df = bt.run()
    assert isinstance(df, pd.DataFrame)


def test_run_none_strategies(monkeypatch):
    bt = IntradayBacktester(["AAPL"], days=1, strategies=None)
    monkeypatch.setattr(
        "hybrid_ai_trading.pipelines.backtest.get_intraday_bars",
        lambda *a, **k: [deepcopy(b) for _ in range(10) for b in fake_bars()],
    )
    df = bt.run()
    assert not df.empty and "Strategy" in df.columns


def test_run_no_callable_strategies(tmp_path):
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"bad": "not_callable"})
    bt.reports_dir = tmp_path
    assert bt.run().empty


def test_run_error_strategy(monkeypatch, tmp_path, caplog):
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"err": always_error})
    bt.reports_dir = tmp_path
    monkeypatch.setattr(
        "hybrid_ai_trading.pipelines.backtest.get_intraday_bars",
        lambda *a, **k: [deepcopy(b) for _ in range(15) for b in fake_bars()],
    )
    with caplog.at_level("ERROR"):
        df = bt.run()
    assert isinstance(df, pd.DataFrame)


def test_run_skips_holiday(monkeypatch, tmp_path):
    class FakeDT(dt.datetime):
        @classmethod
        def today(cls): return dt.datetime(2025, 12, 24)
    monkeypatch.setattr(backtest, "datetime", FakeDT)
    bt = IntradayBacktester(["AAPL"], days=3, strategies={"buy": always_buy})
    monkeypatch.setattr("hybrid_ai_trading.pipelines.backtest.get_intraday_bars",
                        lambda *a, **k: [deepcopy(b) for _ in range(30) for b in fake_bars()])
    df = bt.run()
    assert not df.empty


def test_run_empty_bars(monkeypatch, tmp_path):
    bt = IntradayBacktester(["AAPL"], days=2, strategies={"buy": always_buy})
    monkeypatch.setattr("hybrid_ai_trading.pipelines.backtest.get_intraday_bars",
                        lambda *a, **k: [])
    df = bt.run()
    assert "Strategy" in df.columns


def test_run_sharpe_with_stdev(monkeypatch, tmp_path):
    bt = IntradayBacktester(["AAPL"], days=2, strategies={"buy": always_buy})
    bt.reports_dir = tmp_path
    bt.daily_stop = -999999
    bt.daily_target = 999999
    bt.risk_manager.check_trade = lambda *a, **k: True

    bars_day1 = [{"t": 1_700_000_000_000 + i * 60_000, "c": 100 + i} for i in range(20)]
    bars_day2 = [{"t": 1_700_000_100_000 + i * 60_000, "c": 200 - i} for i in range(20)]

    sequence = [bars_day1, bars_day2]
    monkeypatch.setattr(
        "hybrid_ai_trading.pipelines.backtest.get_intraday_bars", lambda *a, **k: sequence.pop(0)
    )

    df = bt.run()
    sharpe = df["Sharpe"].iloc[0]
    assert sharpe != 0


# --- Plotting ---
def test_plot_equity_and_drawdown_empty(monkeypatch, tmp_path):
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": always_buy})
    bt.reports_dir = tmp_path
    bt._plot_equity("AAPL", [])
    bt._plot_drawdown("AAPL", [])
    assert (tmp_path / "AAPL_equity_curve.png").exists()
    assert (tmp_path / "AAPL_drawdown.png").exists()


def test_plot_equity_and_drawdown_error(monkeypatch, tmp_path, caplog):
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": always_buy})
    bt.reports_dir = tmp_path
    monkeypatch.setattr(backtest.plt, "savefig",
                        lambda *a, **k: (_ for _ in ()).throw(Exception("fail save")))
    with caplog.at_level("ERROR"):
        bt._plot_equity("AAPL", [1, 2, 3])
        bt._plot_drawdown("AAPL", [1, 2, 3])
    assert any("Failed to plot" in m for m in caplog.messages)


# --- Trade Logging ---
def test_log_trade_error(monkeypatch, tmp_path, caplog):
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": always_buy})
    logfile = tmp_path / "log.csv"
    monkeypatch.setattr(pd.DataFrame, "to_csv",
                        lambda *a, **k: (_ for _ in ()).throw(Exception("fail log")))
    with caplog.at_level("ERROR"):
        bt._log_trade(str(logfile), "AAPL", "2025-01-01", {"t": 1}, "BUY", 1, 1, 100)
    assert any("Failed to log trade" in m for m in caplog.messages)


# --- Leaderboard ---
def test_export_leaderboard_sharpe_styles(tmp_path):
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": always_buy})
    bt.reports_dir = tmp_path
    df = pd.DataFrame([
        {"Strategy": "B", "Symbol": "AAPL", "Trades": 1,
         "WinRate %": 100, "AvgDaily PnL": 1, "Total PnL": 10,
         "Final Equity": 1010, "Sharpe": val,
         "Blocked": 0, "Blocked %": 0}
        for val in (-1, 0, 2)
    ])
    bt.export_leaderboard(df)
    html_file = tmp_path / "strategy_leaderboard.html"
    assert html_file.exists()
    text = html_file.read_text()
    assert "Sharpe" in text and "AAPL" in text


def test_export_leaderboard_empty(tmp_path, caplog):
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": always_buy})
    bt.reports_dir = tmp_path
    with caplog.at_level("WARNING"):
        bt.export_leaderboard(pd.DataFrame())
    assert any("leaderboard empty" in m for m in caplog.messages)
