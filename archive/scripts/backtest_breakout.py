"""
Backtest Breakout Strategy (Hybrid AI Quant Pro v16.2 – Hedge-Fund OE Grade)
============================================================================
- Loads OHLCV data
- Applies breakout entry/exit rules via breakout_polygon
- Runs backtest with IntradayBacktester
- Exports trades (CSV) and logs results
- Integrated with hedge-fund OE grade pipeline (results_summary, charts, audit trail)
"""

import logging
from pathlib import Path
import pandas as pd

from hybrid_ai_trading.pipelines.backtest import IntradayBacktester
from hybrid_ai_trading.signals.breakout_polygon import breakout_intraday as breakout_signal

# ------------------------------------------------------
# Logging
# ------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("BacktestBreakout")


# ------------------------------------------------------
# Backtest Runner
# ------------------------------------------------------
def run_backtest(ticker: str, data_path: str = "data", lookback: int = 20, export_csv: bool = False) -> None:
    """
    Run breakout backtest for one ticker.

    Args:
        ticker: Symbol to backtest (e.g. "SPY")
        data_path: Directory containing OHLCV CSVs
        lookback: Breakout lookback window
        export_csv: If True, save trades to results/ as CSV
    """
    path = Path(data_path) / f"{ticker}.csv"
    if not path.exists():
        logger.error("❌ Missing data file: %s", path)
        return

    df = pd.read_csv(path, parse_dates=["date"])
    if df.empty:
        logger.warning("⚠️ Empty dataset for %s", ticker)
        return

    logger.info("🔎 Running breakout backtest on %s", ticker)

    # --- Strategy wiring (IntradayBacktester expects callable on bars)
    strategies = {"breakout": lambda bars: breakout_signal(bars, lookback=lookback)}

    bt = IntradayBacktester([ticker], days=len(df), strategies=strategies)
    bt.reports_dir = "results"
    results = bt.run()

    if results.empty:
        logger.info("ℹ️ No trades for %s", ticker)
        return

    logger.info("✅ Completed breakout backtest for %s | Strategies=%s", ticker, list(bt.results_summary.keys()))
    if export_csv:
        out_path = Path("results") / f"backtest_breakout_{ticker}.csv"
        out_path.parent.mkdir(exist_ok=True)
        results.to_csv(out_path, index=False)
        logger.info("📂 Exported trades: %s", out_path)


# ------------------------------------------------------
# Entrypoint
# ------------------------------------------------------
if __name__ == "__main__":
    run_backtest("SPY", lookback=20, export_csv=True)
