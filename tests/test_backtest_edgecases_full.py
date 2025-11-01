"""
Edge Case Coverage Tests: Backtest Pipeline (v16.7 â€“ Hedge-Fund OE Grade, Full Coverage)
=======================================================================================
Covers ALL branches of backtest.py:
- Config loader (missing, parse fail, not dict, bad keys, none values)
- Data fetcher (no API key, non-200, json parse error, request exception)
- SafeEmptyDataFrame
- Run branches (holiday, no strategies, bad strategy, fill failure, success path)
- Sharpe ratio (positive, negative, zero)
- Plotting error branches
- Leaderboard (empty, fail, success)
"""

import datetime

import pandas as pd
import requests
import yaml

from hybrid_ai_trading.execution.paper_simulator import PaperSimulator
from hybrid_ai_trading.pipelines import backtest
from hybrid_ai_trading.pipelines.backtest import (
    IntradayBacktester,
    _safe_empty_dataframe,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def fake_bars():
    return [{"t": 1, "c": 100}, {"t": 2, "c": 101}]


def always_buy(_):
    return "BUY"


def always_sell(_):
    return "SELL"


def always_error(_):
    raise RuntimeError("bad strat")


# ------------------------------------------------------------------
# Config Loader Edge Cases
# ------------------------------------------------------------------
def test_load_config_errors(tmp_path, caplog):
    # Missing file
    cfg = backtest.load_config(str(tmp_path / "nope.yaml"))
    assert cfg == {}
    assert "missing file" in caplog.text.lower()

    # Not a dict
    f = tmp_path / "not_dict.yaml"
    f.write_text(yaml.dump(["bad", "list"]))
    cfg = backtest.load_config(str(f))
    assert cfg == {}
    assert "must be a dict" in caplog.text.lower()

    # Invalid keys
    f = tmp_path / "bad_keys.yaml"
    f.write_text(yaml.dump({123: "val"}))
    cfg = backtest.load_config(str(f))
    assert cfg == {}
    assert "keys must be strings" in caplog.text.lower()

    # None values
    f = tmp_path / "bad_vals.yaml"
    f.write_text(yaml.dump({"a": None}))
    cfg = backtest.load_config(str(f))
    assert cfg == {}
    assert "values cannot be none" in caplog.text.lower()

    # Parse error
    f = tmp_path / "bad_yaml.yaml"
    f.write_text("::not-yaml::")
    cfg = backtest.load_config(str(f))
    assert cfg == {}
    assert "failed to load" in caplog.text.lower()


# ------------------------------------------------------------------
# Data Fetcher Edge Cases
# ------------------------------------------------------------------
def test_get_intraday_bars_branches(monkeypatch, caplog):
    # No API key
    bars = backtest.get_intraday_bars("AAPL", "2020", "2020", api_key="")
    assert bars == []
    assert "api key missing" in caplog.text.lower()

    # Non-200
    class FakeResp:
        status_code, text = 500, "oops"

    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResp())
    bars = backtest.get_intraday_bars("AAPL", "2020", "2020", "KEY")
    assert bars == []
    assert "error fetching" in caplog.text.lower()

    # JSON error
    class FakeResp2:
        status_code = 200

        def json(self):
            raise ValueError("bad json")

    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResp2())
    bars = backtest.get_intraday_bars("AAPL", "2020", "2020", "KEY")
    assert bars == []
    assert "json parse error" in caplog.text.lower()

    # Request exception
    monkeypatch.setattr(
        requests, "get", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    bars = backtest.get_intraday_bars("AAPL", "2020", "2020", "KEY")
    assert bars == []
    assert "request failed" in caplog.text.lower()


# ------------------------------------------------------------------
# Safe DataFrame
# ------------------------------------------------------------------
def test_safe_empty_dataframe_schema_and_methods():
    df = _safe_empty_dataframe(["a", "b", "Sharpe"])
    assert df.empty
    assert list(df.columns) == ["a", "b", "Sharpe"]
    assert df.to_dict() == {"a": [], "b": [], "Sharpe": []}


# ------------------------------------------------------------------
# Run Branches
# ------------------------------------------------------------------
def test_run_no_strategies(tmp_path, caplog):
    bt = IntradayBacktester(["AAPL"], days=1, strategies={})
    bt.reports_dir = tmp_path
    df = bt.run()
    assert isinstance(df, pd.DataFrame)
    assert "no strategies configured" in caplog.text.lower()


def test_run_holiday(monkeypatch, tmp_path, caplog):
    class FakeDate(datetime.date):
        @classmethod
        def today(cls):
            return datetime.date(2025, 12, 25)

    monkeypatch.setattr(backtest.datetime, "date", FakeDate)
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": always_buy})
    bt.reports_dir = tmp_path
    df = bt.run()
    assert "HOLIDAY" in df.iloc[0]["Symbol"]
    assert "skipping run" in caplog.text.lower()


def test_strategy_exception(monkeypatch, tmp_path, caplog):
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"bad": always_error})
    bt.reports_dir = tmp_path
    monkeypatch.setattr(backtest, "get_intraday_bars", lambda *a, **k: fake_bars())
    df = bt.run()
    assert isinstance(df, pd.DataFrame)
    assert "strategy always_error failed" in caplog.text.lower()


def test_fill_failure(monkeypatch, tmp_path, caplog):
    def bad_fill(*_a, **_k):
        raise Exception("boom fill")

    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": always_buy})
    bt.reports_dir = tmp_path
    monkeypatch.setattr(PaperSimulator, "simulate_fill", bad_fill)
    df = bt.run()
    assert isinstance(df, pd.DataFrame)
    assert "fill simulation failed" in caplog.text.lower()


# ------------------------------------------------------------------
# Sharpe Ratio Branches
# ------------------------------------------------------------------
def test_sharpe_positive_negative_zero(monkeypatch, tmp_path):
    # Positive
    bt = IntradayBacktester(["AAPL"], days=3, strategies={"buy": always_buy})
    bt.reports_dir = tmp_path
    monkeypatch.setattr(backtest, "get_intraday_bars", lambda *a, **k: fake_bars())
    assert bt.run()["Sharpe"].iloc[0] > 0

    # Negative
    bt = IntradayBacktester(["AAPL"], days=3, strategies={"sell": always_sell})
    bt.reports_dir = tmp_path
    monkeypatch.setattr(backtest, "get_intraday_bars", lambda *a, **k: fake_bars())
    assert bt.run()["Sharpe"].iloc[0] < 0

    # Zero
    bt = IntradayBacktester(["AAPL"], days=3, strategies={"flat": lambda _: "HOLD"})
    bt.reports_dir = tmp_path
    monkeypatch.setattr(backtest, "get_intraday_bars", lambda *a, **k: fake_bars())
    assert bt.run()["Sharpe"].iloc[0] == 0.0


# ------------------------------------------------------------------
# Plotting
# ------------------------------------------------------------------
def test_plot_equity_and_drawdown_exceptions(monkeypatch, tmp_path, caplog):
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": always_buy})
    bt.reports_dir = tmp_path
    monkeypatch.setattr(
        backtest.plt,
        "savefig",
        lambda *a, **k: (_ for _ in ()).throw(Exception("fail")),
    )
    with caplog.at_level("ERROR"):
        bt._plot_equity("AAPL", [1, 2, 3])
        bt._plot_drawdown("AAPL", [1, 2, 3])
    assert "plot equity failed" in caplog.text.lower()
    assert "plot drawdown failed" in caplog.text.lower()


# ------------------------------------------------------------------
# Leaderboard Export
# ------------------------------------------------------------------
def test_export_leaderboard_empty_and_exception(tmp_path, caplog):
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": always_buy})
    bt.reports_dir = tmp_path
    df = _safe_empty_dataframe(["Strategy", "Symbol", "Sharpe"])
    bt.export_leaderboard(df)
    assert "empty dataframe" in caplog.text.lower()

    class BadDF:
        empty = False

        def to_excel(self, *a, **k):
            raise Exception("excel fail")

        @property
        def style(self):
            class S:
                def to_html(self, *a, **k):
                    raise Exception("html fail")

            return S()

    with caplog.at_level("ERROR"):
        bt.export_leaderboard(BadDF())
    assert "failed to export leaderboard" in caplog.text.lower()


def test_export_leaderboard_success(tmp_path):
    """Covers happy path for leaderboard export (Excel + HTML)."""
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": always_buy})
    bt.reports_dir = tmp_path
    df = pd.DataFrame([{"Strategy": "BUY", "Symbol": "AAPL", "Sharpe": 1.0}])
    bt.export_leaderboard(df)
    assert (tmp_path / "strategy_leaderboard.xlsx").exists()
    assert (tmp_path / "strategy_leaderboard.html").exists()


def test_strategy_runtime_error(monkeypatch, tmp_path, caplog):
    """Force a runtime error inside strategy â†’ should log 'strategy ... failed'."""

    def bad_strategy(_bars):
        return 1 / 0  # raises ZeroDivisionError

    bt = IntradayBacktester(["AAPL"], days=1, strategies={"bad": bad_strategy})
    bt.reports_dir = tmp_path
    monkeypatch.setattr(backtest, "get_intraday_bars", lambda *a, **k: fake_bars())

    df = bt.run()

    assert isinstance(df, pd.DataFrame)
    assert "strategy bad_strategy failed" in caplog.text.lower()


def test_load_config_file_open_error(monkeypatch, tmp_path, caplog):
    """Simulate file open error to hit early load_config exception branch."""
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("key: val")
    monkeypatch.setattr(
        "builtins.open",
        lambda *a, **k: (_ for _ in ()).throw(PermissionError("no access")),
    )
    cfg = backtest.load_config(str(bad_file))
    assert cfg == {}
    assert "failed to load" in caplog.text.lower()


def test_call_strategy_typeerror(monkeypatch, tmp_path, caplog):
    """Hit the except TypeError branch in _call_strategy (dict-only strategy)."""

    def dict_only_strategy(arg):
        # Fail if bars is not dict
        if not isinstance(arg, dict):
            raise TypeError("dict required")
        return "BUY"

    bt = IntradayBacktester(
        ["AAPL"], days=1, strategies={"dict_only": dict_only_strategy}
    )
    bt.reports_dir = tmp_path
    # Force bars to be list, so first call raises TypeError
    monkeypatch.setattr(backtest, "get_intraday_bars", lambda *a, **k: fake_bars())
    df = bt.run()
    assert "dict_only" in bt.results_summary


def test_fill_failure_exception(monkeypatch, tmp_path, caplog):
    """Force simulate_fill to raise to hit fill simulation exception branch."""
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": always_buy})
    bt.reports_dir = tmp_path

    def bad_fill(*_a, **_k):
        raise RuntimeError("sim fill exploded")

    monkeypatch.setattr(PaperSimulator, "simulate_fill", bad_fill)
    monkeypatch.setattr(backtest, "get_intraday_bars", lambda *a, **k: fake_bars())

    df = bt.run()
    assert "fill simulation failed" in caplog.text.lower()


def test_unexpected_error_outer(monkeypatch, tmp_path, caplog):
    """Force outer unexpected error branch by breaking writerow()."""
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": always_buy})
    bt.reports_dir = tmp_path
    monkeypatch.setattr(backtest, "get_intraday_bars", lambda *a, **k: fake_bars())

    # Patch csv.writer to return an object whose writerow() raises
    class BadWriter:
        def writerow(self, *_a, **_k):
            raise Exception("csv fail")

    def bad_writer(*_a, **_k):
        return BadWriter()

    monkeypatch.setattr(backtest.csv, "writer", bad_writer)

    # Run should catch this in the outer exception handler
    df = bt.run()
    assert isinstance(df, pd.DataFrame)
    assert "unexpected error" in caplog.text.lower()


def test_load_config_open_error(monkeypatch, tmp_path, caplog):
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("foo: bar")
    monkeypatch.setattr(
        "builtins.open",
        lambda *a, **k: (_ for _ in ()).throw(PermissionError("denied")),
    )
    cfg = backtest.load_config(str(bad_file))
    assert cfg == {}
    assert "failed to load" in caplog.text.lower()


def test_plot_equity_failure(monkeypatch, tmp_path, caplog):
    bt = IntradayBacktester(["AAPL"], days=1, strategies={})
    bt.reports_dir = tmp_path
    monkeypatch.setattr(
        backtest.plt,
        "savefig",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fail save")),
    )
    with caplog.at_level("ERROR"):
        bt._plot_equity("AAPL", [100, 200])
    assert "plot equity failed" in caplog.text.lower()


def test_export_leaderboard_failure(monkeypatch, tmp_path, caplog):
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": lambda _: "BUY"})
    bt.reports_dir = tmp_path
    df = pd.DataFrame([{"Strategy": "BUY", "Symbol": "AAPL", "Sharpe": 1.0}])
    # Patch ExcelWriter to raise
    monkeypatch.setattr(
        backtest.pd,
        "ExcelWriter",
        lambda *a, **k: (_ for _ in ()).throw(Exception("excel fail")),
    )
    with caplog.at_level("ERROR"):
        bt.export_leaderboard(df)
    assert "failed to export leaderboard" in caplog.text.lower()
