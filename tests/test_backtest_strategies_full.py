"""
Backtest Strategies & Pipeline Suite (Hybrid AI Quant Pro v16.7 – Hedge-Fund OE Grade)
======================================================================================
- Covers real strategy functions (Breakout, MA, RSI, Bollinger, MACD, VWAP)
- Lambda signals sanity (BUY, SELL, HOLD)
- RiskManager block paths + daily stop/target
- Leaderboard (Excel + HTML)
- Chart + CSV generation
- Performance (<2s)
"""

import time
import pandas as pd
import pytest
from hybrid_ai_trading.pipelines.backtest import IntradayBacktester
from hybrid_ai_trading.signals import (
    breakout_intraday,
    moving_average_signal,
    rsi_signal,
    bollinger_bands_signal,
    macd_signal,
    vwap_signal,
)


# --- Fixtures -----------------------------------------------------
@pytest.fixture
def fake_bars():
    return [
        {"t": 1, "c": 100, "h": 101, "l": 99, "o": 100, "v": 1000},
        {"t": 2, "c": 102, "h": 103, "l": 101, "o": 101, "v": 1000},
        {"t": 3, "c": 104, "h": 105, "l": 103, "o": 103, "v": 1000},
        {"t": 4, "c": 101, "h": 102, "l": 100, "o": 101, "v": 1000},
        {"t": 5, "c": 99, "h": 100, "l": 98, "o": 99, "v": 1000},
    ]


@pytest.fixture(autouse=True)
def patch_polygon(monkeypatch, fake_bars):
    """Patch Polygon data fetcher with deterministic fake bars."""
    monkeypatch.setattr(
        "hybrid_ai_trading.pipelines.backtest.get_intraday_bars",
        lambda ticker, start, end, api_key=None, interval="1", timespan="minute": list(fake_bars),
    )


# --- Lambda Signals ----------------------------------------------
@pytest.mark.parametrize("forced_signal", ["BUY", "SELL", "HOLD"])
def test_backtester_runs_with_lambdas(tmp_path, forced_signal):
    strategies = {
        name: (lambda bars, sig=forced_signal: sig)
        for name in ["breakout", "ma", "rsi", "bollinger", "macd", "vwap"]
    }
    bt = IntradayBacktester(symbols=["AAPL"], days=2, strategies=strategies)
    bt.reports_dir = tmp_path
    df = bt.run()

    for strat in strategies:
        assert strat in bt.results_summary
        assert "AAPL" in bt.results_summary[strat]

    # Export leaderboard
    bt.export_leaderboard(df)
    excel_file = tmp_path / "strategy_leaderboard.xlsx"
    html_file = tmp_path / "strategy_leaderboard.html"
    assert excel_file.exists()
    assert html_file.exists()

    df_excel = pd.read_excel(excel_file)
    assert {"Strategy", "Symbol", "Sharpe"}.issubset(df_excel.columns)

    assert (tmp_path / "AAPL_equity_curve.png").exists()
    assert (tmp_path / "AAPL_drawdown.png").exists()
    assert list(tmp_path.glob("backtest_*.csv"))


# --- Real Strategies ---------------------------------------------
@pytest.mark.parametrize(
    "name,strategy",
    [
        ("breakout", breakout_intraday),
        ("ma", moving_average_signal),
        ("rsi", rsi_signal),
        ("bollinger", bollinger_bands_signal),
        ("macd", macd_signal),
        ("vwap", vwap_signal),
    ],
)
def test_backtester_runs_with_real_strategy(tmp_path, name, strategy):
    if strategy is None:
        pytest.skip(f"{name} not implemented")

    bt = IntradayBacktester(["AAPL"], days=2, strategies={name: strategy})
    bt.reports_dir = tmp_path
    df = bt.run()

    # Export leaderboard for consistency
    bt.export_leaderboard(df)
    metrics = bt.results_summary[name]["AAPL"]
    required_keys = {"Sharpe", "Trades", "WinRate %", "Blocked %", "FinalEquity"}
    assert required_keys.issubset(metrics.keys())

    excel_file = tmp_path / "strategy_leaderboard.xlsx"
    df_excel = pd.read_excel(excel_file)
    assert name.upper() in df_excel["Strategy"].values


# --- Risk Manager / Stop-Target Paths ----------------------------
def test_risk_manager_block(tmp_path, fake_bars):
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": lambda _: "BUY"})
    bt.reports_dir = tmp_path
    bt.risk_manager.check_trade = lambda pnl: False
    df = bt.run()
    assert not df.empty


def test_daily_stop_and_target(tmp_path, fake_bars):
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": lambda _: "BUY"})
    bt.reports_dir = tmp_path
    bt.daily_stop, bt.daily_target = -0.0001, 0.0001
    df = bt.run()
    assert not df.empty


# --- Performance -------------------------------------------------
@pytest.mark.slow
def test_backtest_strategies_runs_fast(tmp_path):
    strategies = {
        "breakout": breakout_intraday,
        "ma": moving_average_signal,
        "rsi": rsi_signal,
        "bollinger": bollinger_bands_signal,
        "macd": macd_signal,
        "vwap": vwap_signal,
    }
    bt = IntradayBacktester(["AAPL"], days=2, strategies=strategies)
    bt.reports_dir = tmp_path
    start = time.perf_counter()
    df = bt.run()

    bt.export_leaderboard(df)
    duration = time.perf_counter() - start
    assert not df.empty
    assert duration < 2.0


def test_leaderboard_html_contains_strategy(tmp_path):
    bt = IntradayBacktester(["AAPL"], days=1, strategies={"buy": lambda _: "BUY"})
    bt.reports_dir = tmp_path
    df = bt.run()

    bt.export_leaderboard(df)
    html_file = tmp_path / "strategy_leaderboard.html"
    assert html_file.exists()

    content = html_file.read_text(encoding="utf-8")
    assert "BUY" in content.upper() or "AAPL" in content
