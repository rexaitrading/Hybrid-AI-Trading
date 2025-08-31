import os
import pytest
from src.pipelines.backtest import IntradayBacktester

def test_backtester_runs_with_mock(monkeypatch, tmp_path):
    # Patch Polygon API fetcher to return dummy bars
    monkeypatch.setattr(
        "src.pipelines.backtest.get_intraday_bars",
        lambda symbol, start, end, **kwargs: [
            {"t": 1, "c": 100, "h": 101, "l": 99, "o": 100, "v": 1000},
            {"t": 2, "c": 102, "h": 103, "l": 101, "o": 101, "v": 1000},
            {"t": 3, "c": 104, "h": 105, "l": 103, "o": 103, "v": 1000},
        ]
    )

    reports_dir = tmp_path / "reports"
    backtester = IntradayBacktester(symbols=["AAPL"], days=1)
    backtester.reports_dir = str(reports_dir)
    backtester.run()

    # Check outputs exist
    assert "AAPL" in backtester.results_summary
    assert (reports_dir / "intraday_backtest.csv").exists()
    assert (reports_dir / "AAPL_equity_curve.png").exists()
    assert (reports_dir / "AAPL_drawdown.png").exists()
