"""
Quant Pro Backtest Driver (Hybrid AI Quant Pro v26.0 – Hedge Fund Level)
------------------------------------------------------------------------
Responsibilities:
- Load configuration (risk, costs, strategy params)
- Initialize ExecutionEngine with RiskManager, PortfolioTracker, PaperSimulator
- Fetch historical data from Polygon (equities) or CCXT (crypto)
- Route trades through ExecutionEngine
- Track performance metrics (ROI, Sharpe, Sortino, Calmar, etc.)
- Save audit logs + performance snapshot (JSON)
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import ccxt
import pandas as pd
import requests

# ---------------------------------------------------------------------
# Ensure src/ is importable
# ---------------------------------------------------------------------
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from hybrid_ai_trading.execution import ExecutionEngine  # noqa: E402
from hybrid_ai_trading.performance_tracker import PerformanceTracker  # noqa: E402

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("QuantProBacktest")


# ---------------------------------------------------------------------
# Data Loaders
# ---------------------------------------------------------------------
def load_data_polygon(symbol: str, start: str, end: str, api_key: str) -> pd.DataFrame:
    """Fetch OHLCV bars from Polygon.io."""
    url = (
        f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start}/{end}"
        f"?adjusted=true&sort=asc&apiKey={api_key}"
    )
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json().get("results", [])
    if not data:
        raise ValueError(f"No Polygon data returned for {symbol}")
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["t"], unit="ms")
    df.rename(columns={"c": "close"}, inplace=True)
    return df[["timestamp", "close"]]


def load_data_ccxt(
    symbol: str, start: str, end: str, exchange: str = "binance"
) -> pd.DataFrame:
    """Fetch OHLCV bars from CCXT exchange."""
    ex = getattr(ccxt, exchange)()
    since = int(pd.Timestamp(start).timestamp() * 1000)
    ohlcv = ex.fetch_ohlcv(symbol, timeframe="1d", since=since, limit=500)
    df = pd.DataFrame(
        ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df[df["timestamp"] <= pd.Timestamp(end)]
    return df[["timestamp", "close"]]


# ---------------------------------------------------------------------
# Main Backtest
# ---------------------------------------------------------------------
def main() -> None:
    """Run backtest using ExecutionEngine + PerformanceTracker."""

    # === Config (stub – replace with YAML loader later) ===
    config: Dict[str, Any] = {
        "risk": {
            "daily_loss_limit": -0.03,
            "trade_loss_limit": -0.01,
            "max_leverage": 5.0,
            "max_portfolio_exposure": 0.5,
            "max_drawdown": -0.2,
            "roi_min": -0.2,
            "sharpe_min": 0.5,
            "sortino_min": 0.5,
        },
        "costs": {
            "slippage_pct": 0.001,
            "commission_pct": 0.0005,
            "commission_per_share": 0.005,
            "min_commission": 1.0,
        },
        "dry_run": True,
    }

    # === Initialize Engine ===
    engine = ExecutionEngine(dry_run=True, config=config)
    perf = PerformanceTracker(window=250)

    # === Fetch real data (example: AAPL from Polygon) ===
    api_key = os.getenv("POLYGON_KEY", "")
    if not api_key:
        logger.error("❌ POLYGON_KEY not found in environment")
        return

    df = load_data_polygon("AAPL", "2025-01-01", "2025-01-10", api_key)

    logger.info("🚀 Starting backtest on %d bars", len(df))

    for _, row in df.iterrows():
        ts: datetime = row["timestamp"].to_pydatetime()
        price: float = row["close"]

        # === Strategy stub: naive trend-follow ===
        signal = "BUY" if price > 190 else "SELL"
        result = engine.place_order("AAPL", signal, qty=10, price=price)

        # === Record equity + PnL ===
        snapshot = engine.portfolio_tracker.report()
        perf.record_equity(snapshot["equity"], ts)
        if result.get("status") == "filled":
            perf.record_trade(snapshot["realized_pnl"])

    # === Final Report ===
    metrics = perf.snapshot()
    logger.info("📈 Final Performance Metrics:")
    for k, v in metrics.items():
        logger.info("  %-15s %s", k, v)

    # === Export snapshot ===
    Path("reports").mkdir(exist_ok=True)
    out_path = Path("reports/performance_snapshot.json")
    perf.export_json(str(out_path))
    logger.info("✅ Performance snapshot saved → %s", out_path)


# ---------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------
if __name__ == "__main__":
    main()
