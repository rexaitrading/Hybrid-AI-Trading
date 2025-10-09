"""
Backtest Pipeline Test (Hybrid AI Quant Pro v16.2 – Hedge-Fund OE Grade)
========================================================================
- Validates IntradayBacktester runs end-to-end with mocked data.
- Ensures results_summary has dict[strategy][symbol] metrics.
- Ensures CSV, equity, and drawdown charts are generated.
"""

import csv

from hybrid_ai_trading.pipelines.backtest import IntradayBacktester


def test_backtester_runs_with_mock(monkeypatch, tmp_path):
    """Run IntradayBacktester with patched intraday bars."""
    # --- Patch data fetcher to return deterministic dummy bars ---
    monkeypatch.setattr(
        "hybrid_ai_trading.pipelines.backtest.get_intraday_bars",
        lambda symbol, start, end, api_key=None, **kwargs: [
            {"t": 1, "c": 100, "h": 101, "l": 99, "o": 100, "v": 1000},
            {"t": 2, "c": 102, "h": 103, "l": 101, "o": 101, "v": 1000},
            {"t": 3, "c": 104, "h": 105, "l": 103, "o": 103, "v": 1000},
        ],
    )

    # --- Temporary output directory ---
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # --- Run backtester with a strict dummy strategy ---
    def dummy_strategy(data):
        # Handle both call patterns: fn(bars) or fn({"symbol":..., "bars": bars})
        if isinstance(data, dict) and "bars" in data:
            bars = data["bars"]
        else:
            bars = data
        return "BUY" if bars else "HOLD"

    strategies = {"dummy": dummy_strategy}
    backtester = IntradayBacktester(symbols=["AAPL"], days=1, strategies=strategies)
    backtester.reports_dir = str(reports_dir)
    df = backtester.run()

    # --- Assertions: results_summary structure ---
    assert isinstance(backtester.results_summary, dict), "results_summary must be dict"
    assert "dummy" in backtester.results_summary, "Strategy key missing"
    assert "AAPL" in backtester.results_summary["dummy"], "Symbol key missing"

    metrics = backtester.results_summary["dummy"]["AAPL"]
    required_keys = {"Sharpe", "Trades", "WinRate %", "Blocked %", "FinalEquity"}
    assert required_keys.issubset(
        metrics.keys()
    ), f"Missing metrics: {required_keys - set(metrics.keys())}"

    # --- Assertions: DataFrame integrity ---
    assert not df.empty, "Backtester run() must return a non-empty DataFrame"
    assert {"Strategy", "Symbol", "Sharpe"}.issubset(
        df.columns
    ), "Missing required DataFrame columns"

    # --- Assertions: CSV + charts exist ---
    csv_files = list(reports_dir.glob("backtest_*.csv"))
    assert csv_files, "No backtest CSVs generated"
    with open(csv_files[0], "r", encoding="utf-8") as f:
        headers = next(csv.reader(f))
        expected = {
            "symbol",
            "date",
            "time",
            "signal",
            "trade_pnl",
            "daily_pnl",
            "cum_equity",
        }
        assert expected.issubset(
            headers
        ), f"CSV headers missing: {expected - set(headers)}"

    assert (reports_dir / "AAPL_equity_curve.png").exists(), "Equity curve PNG missing"
    assert (reports_dir / "AAPL_drawdown.png").exists(), "Drawdown PNG missing"
