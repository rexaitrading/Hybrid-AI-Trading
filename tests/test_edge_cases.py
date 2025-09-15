"""
Edge Case Coverage Tests: Backtest Pipeline (Hybrid AI Quant Pro v8.7)
======================================================================
Purpose:
- Cover ALL remaining uncovered lines & branches in backtest.py
- Focus on: config loader, holiday skips, empty bars,
  strategy error, fill error, RiskManager block,
  plotting failures, leaderboard export failures.
"""

import os
import pytest
import pandas as pd
import datetime as dt
import yaml
from hybrid_ai_trading.pipelines import backtest
from hybrid_ai_trading.pipelines.backtest import IntradayBacktester


# === Helpers =========================================================
def fake_bars():
    return [
        {"t": 1_700_000_000_000, "c": 100},
        {"t": 1_700_000_060_000, "c": 101},
        {"t": 1_700_000_120_000, "c": 102},
        {"t": 1_700_000_180_000, "c": 103},
    ]


def always_buy(_): 
    return "BUY"


def always_error(_): 
    raise RuntimeError("bad strat")


# === Config Loader Edge Cases (lines 41–63) ==========================
def test_load_config_not_dict(tmp_path, caplog):
    """Ensure non-dict YAML config triggers error logging + safe {} return."""
    bad = tmp_path / "bad.yaml"
    bad.write_text(yaml.dump(["not-a-dict"]))  # valid YAML but not dict
    with caplog.at_level("ERROR"):
        cfg = backtest.load_config(str(bad))
    assert cfg == {}

    # ✅ log message comes from logger.error in backtest.py
    log_msg = caplog.text.lower()
    assert "failed to load" in log_msg
    assert "config" in log_msg
    assert "dict" in log_msg


# === Holiday Skip (line 142) =========================================
def test_run_skips_holiday(monkeypatch, tmp_path):
    """Ensure holiday dates are skipped in run() loop."""
    class FakeDT(dt.datetime):
        @classmethod
        def today(cls):
            return dt.datetime(2025, 12, 24)  # ensures Dec 25 in loop
    monkeypatch.setattr(backtest, "datetime", FakeDT)

    bt = IntradayBacktester(["AAPL"], days=3, strategies={"buy": always_buy})
    monkeypatch.setattr(
        "hybrid_ai_trading.pipelines.backtest.get_intraday_bars",
        lambda *a, **k: fake_bars() * 20
    )
    bt.reports_dir = tmp_path
    df = bt.run()

    assert not df.empty
    # ✅ ensure Dec 25 holiday does not appear in results
    assert all("2025-12-25" not in str(r) for r in df.to_dict("records"))


# === Empty Bars (line 170–171) =======================================
def test_run_empty_bars(monkeypatch, tmp_path):
    """If no bars are returned, leaderboard still generates safely."""
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": always_buy})
    monkeypatch.setattr(
        "hybrid_ai_trading.pipelines.backtest.get_intraday_bars",
        lambda *a, **k: []  # no bars
    )
    df = bt.run()
    assert isinstance(df, pd.DataFrame)
    # ✅ Even with 0 trades, leaderboard still has columns
    assert "Strategy" in df.columns


# === Strategy Exception (line 199) ===================================
def test_strategy_exception(monkeypatch, tmp_path, caplog):
    """If strategy raises error, it should log and continue."""
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"bad": always_error})
    monkeypatch.setattr(
        "hybrid_ai_trading.pipelines.backtest.get_intraday_bars",
        lambda *a, **k: fake_bars() * 30
    )
    bt.reports_dir = tmp_path
    with caplog.at_level("ERROR"):
        df = bt.run()
    assert "strategy" in caplog.text.lower()
    assert isinstance(df, pd.DataFrame)


# === Fill Failure (line 204–206) =====================================
def test_fill_failure(monkeypatch, tmp_path, caplog):
    """If PaperSimulator.simulate_fill raises, log error + continue."""
    def bad_fill(*a, **k): 
        raise Exception("boom fill")

    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": always_buy})
    bt.reports_dir = tmp_path
    monkeypatch.setattr(
        "hybrid_ai_trading.pipelines.backtest.get_intraday_bars",
        lambda *a, **k: fake_bars() * 30
    )
    monkeypatch.setattr(
        "hybrid_ai_trading.execution.paper_simulator.PaperSimulator.simulate_fill",
        bad_fill
    )

    with caplog.at_level("ERROR"):
        df = bt.run()
    assert "fill simulation failed" in caplog.text.lower()


# === RiskManager Block (line 219) ====================================
def test_riskmanager_blocked(monkeypatch, tmp_path):
    """If RiskManager blocks trade, 'BLOCKED' should be logged to CSV."""
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": always_buy})
    bt.risk_manager.check_trade = lambda pnl: False  # force block
    bt.reports_dir = tmp_path

    monkeypatch.setattr(
        "hybrid_ai_trading.pipelines.backtest.get_intraday_bars",
        lambda *a, **k: fake_bars() * 25
    )

    df = bt.run()
    log_file = list(tmp_path.glob("backtest_*.csv"))[0]
    assert "BLOCKED" in log_file.read_text()


# === Plot Exceptions (lines 252, 258–259) =============================
def test_plot_exceptions(monkeypatch, tmp_path, caplog):
    """Force matplotlib save/figure failures → should log error."""
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": always_buy})
    bt.reports_dir = tmp_path

    monkeypatch.setattr(backtest.plt, "savefig",
                        lambda *a, **k: (_ for _ in ()).throw(Exception("save fail")))
    monkeypatch.setattr(backtest.plt, "figure",
                        lambda *a, **k: (_ for _ in ()).throw(Exception("fig fail")))

    with caplog.at_level("ERROR"):
        bt._plot_equity("AAPL", [100])
        bt._plot_drawdown("AAPL", [100])
    assert "failed to plot" in caplog.text.lower()


# === Leaderboard Export (lines 318–361) ===============================
def test_export_leaderboard_failures(monkeypatch, tmp_path, caplog):
    """Ensure leaderboard export handles Excel/HTML failures gracefully."""
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": always_buy})
    bt.reports_dir = tmp_path
    df = pd.DataFrame([{
        "Strategy": "B", "Symbol": "AAPL", "Trades": 1,
        "WinRate %": 100, "AvgDaily PnL": 1, "Total PnL": 10,
        "Final Equity": 1010, "Sharpe": 2,
        "Blocked": 0, "Blocked %": 0
    }])

    # Excel writer fails
    class BadWriter:
        def __enter__(self): 
            raise Exception("writer fail")
        def __exit__(self, *a): 
            return False
    monkeypatch.setattr(pd, "ExcelWriter", lambda *a, **k: BadWriter())

    with caplog.at_level("ERROR"):
        bt.export_leaderboard(df)
    assert "failed to export leaderboard" in caplog.text.lower()

    # Style.to_html fails
    class DummyStyle:
        def map(self, *a, **k): 
            return self
        def to_html(self, *a, **k): 
            raise Exception("style fail")
    monkeypatch.setattr(pd.DataFrame, "style", property(lambda self: DummyStyle()))

    with caplog.at_level("ERROR"):
        bt.export_leaderboard(df)
    assert "failed to export leaderboard" in caplog.text.lower()
