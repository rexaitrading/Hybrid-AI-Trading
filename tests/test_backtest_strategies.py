"""
Test Backtester with All Strategies (Breakout, MA, RSI, Bollinger, MACD, VWAP)

Covers:
1. Lambda signals → quick pipeline sanity check
2. Real strategy functions → integration test with mocked fake bars
3. Performance benchmarking → timing per strategy
4. Risk metrics validation (blocked %, Sharpe sanity check)
"""

import os
import time
import pandas as pd
import pytest
from src.pipelines.backtest import IntradayBacktester
from src.signals import (
    breakout_intraday,
    moving_average_signal,
    rsi_signal,
    bollinger_bands_signal,
    macd_signal,
    vwap_signal,
)

# ==========================================================
# Fixtures
# ==========================================================
@pytest.fixture
def fake_bars():
    """Fake intraday OHLCV bars"""
    return [
        {"t": 1, "c": 100, "h": 101, "l": 99, "o": 100, "v": 1000},
        {"t": 2, "c": 102, "h": 103, "l": 101, "o": 101, "v": 1000},
        {"t": 3, "c": 104, "h": 105, "l": 103, "o": 103, "v": 1000},
        {"t": 4, "c": 101, "h": 102, "l": 100, "o": 101, "v": 1000},
        {"t": 5, "c": 99,  "h": 100, "l": 98,  "o": 99,  "v": 1000},
    ]


@pytest.fixture(autouse=True)
def patch_polygon(monkeypatch, fake_bars):
    """Patch Polygon fetcher to always return fake bars"""
    monkeypatch.setattr(
        "src.pipelines.backtest.get_intraday_bars",
        lambda ticker, start, end, api_key, interval="1", timespan="minute": fake_bars,
    )

# ==========================================================
# Functional Tests
# ==========================================================
@pytest.mark.parametrize("forced_signal", ["BUY", "SELL", "HOLD"])
def test_backtester_runs_with_lambdas(tmp_path, forced_signal):
    """Quick sanity check using forced lambda signals for all strategies"""
    symbols = ["AAPL"]
    strategies = {
        "breakout": lambda bars: forced_signal,
        "ma": lambda bars: forced_signal,
        "rsi": lambda bars: forced_signal,
        "bollinger": lambda bars: forced_signal,
        "macd": lambda bars: forced_signal,
        "vwap": lambda bars: forced_signal,
    }

    backtester = IntradayBacktester(symbols=symbols, days=2, strategies=strategies)
    backtester.reports_dir = tmp_path
    backtester.run()

    for strat in strategies:
        assert strat in backtester.results_summary
        assert "AAPL" in backtester.results_summary[strat]

    # Leaderboard check
    excel_file = tmp_path / "strategy_leaderboard.xlsx"
    df = pd.read_excel(excel_file)
    expected_cols = {"Strategy", "Symbol", "Trades", "WinRate %", "Sharpe"}
    assert expected_cols.issubset(df.columns)


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
    """Run each real strategy independently on fake bars"""
    if strategy is None:
        pytest.skip(f"{name} strategy not implemented")

    symbols = ["AAPL"]
    backtester = IntradayBacktester(symbols=symbols, days=2, strategies={name: strategy})
    backtester.reports_dir = tmp_path
    backtester.run()

    assert name in backtester.results_summary
    metrics = backtester.results_summary[name]["AAPL"]

    # Sanity checks
    assert isinstance(metrics["final_equity"], (int, float))
    assert "sharpe" in metrics
    assert 0 <= metrics["blocked_pct"] <= 100

    # Leaderboard contains strategy
    excel_file = tmp_path / "strategy_leaderboard.xlsx"
    df = pd.read_excel(excel_file)
    assert df["Strategy"].str.upper().str.contains(name.upper()).any()

# ==========================================================
# Performance Benchmarks
# ==========================================================
@pytest.mark.perf
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
def test_strategy_runtime_benchmark(tmp_path, name, strategy):
    """Benchmark runtime per strategy (must stay under threshold)"""
    if strategy is None:
        pytest.skip(f"{name} strategy not implemented")

    symbols = ["AAPL"]
    backtester = IntradayBacktester(symbols=symbols, days=5, strategies={name: strategy})
    backtester.reports_dir = tmp_path

    start = time.time()
    backtester.run()
    elapsed = time.time() - start

    # Performance threshold (adjustable for your system)
    assert elapsed < 3.0, f"{name} strategy too slow: {elapsed:.2f}s"
