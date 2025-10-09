"""
Backtest Harness (Hybrid AI Quant Pro v16.3 – Hedge-Fund OE Grade)
==================================================================
- Multi-symbol historical backtests with TradeEngine
- Loads OHLCV data from /data/*.csv
- Example MA20 crossover strategy
- Exports Excel + PNG + TXT reports
- Attribution by symbol + sector
- Hedge-fund grade logging & safety checks
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

# 🔑 Ensure src/ is on Python path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from hybrid_ai_trading.trade_engine import TradeEngine  # noqa

SECTOR_MAP = {"BTC/USDT": "Crypto", "ETH/USDT": "Crypto", "SPY": "Equities"}

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("BacktestHarness")


# ==========================================================
# Data Loader
# ==========================================================
def load_historical_data(symbol: str) -> pd.DataFrame:
    """Load OHLCV data from /data/ folder."""
    fname = Path("data") / f"{symbol.replace('/', '_')}.csv"
    if not fname.exists():
        logger.error("❌ No data file for %s (expected %s)", symbol, fname)
        raise FileNotFoundError(f"No data file for {symbol}. Expected {fname}")
    df = pd.read_csv(fname, parse_dates=["date"])
    if "close" not in df.columns:
        raise ValueError(f"CSV for {symbol} missing 'close' column")
    return df


# ==========================================================
# Strategy Runner
# ==========================================================
def run_backtest(engine: TradeEngine, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Run MA20 crossover strategy for a single symbol."""
    trades = []
    data["MA20"] = data["close"].rolling(20).mean()

    for _, row in data.iterrows():
        if pd.isna(row["MA20"]):
            continue

        signal = "HOLD"
        if row["close"] > row["MA20"]:
            signal = "BUY"
        elif row["close"] < row["MA20"]:
            signal = "SELL"

        result = engine.process_signal(
            symbol, signal, size=1, price=float(row["close"])
        )
        engine.portfolio.update_equity({symbol: float(row["close"])})

        trades.append(
            {
                "date": row["date"],
                "symbol": symbol,
                "signal": signal,
                "price": float(row["close"]),
                "status": result.get("status", "unknown"),
                "equity": engine.get_equity(),
            }
        )
    return pd.DataFrame(trades)


# ==========================================================
# Results Export
# ==========================================================
def save_results(
    all_trades: pd.DataFrame, summary: dict, attribution: dict, tag="multi"
) -> None:
    """Save results to Excel, PNG, TXT."""
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Excel
    excel_path = reports_dir / f"backtest_{tag}_{timestamp}.xlsx"
    with pd.ExcelWriter(excel_path, engine="xlsxwriter") as writer:
        all_trades.to_excel(writer, sheet_name="Trades", index=False)
        all_trades[["date", "equity"]].to_excel(
            writer, sheet_name="EquityCurve", index=False
        )
        pd.DataFrame.from_dict(summary, orient="index", columns=["Value"]).to_excel(
            writer, sheet_name="Summary"
        )
        pd.DataFrame.from_dict(attribution, orient="index", columns=["PnL"]).to_excel(
            writer, sheet_name="Attribution"
        )

    # PNG equity curve
    chart_path = reports_dir / f"backtest_{tag}_{timestamp}.png"
    plt.figure(figsize=(12, 6))
    plt.plot(
        all_trades["date"],
        all_trades["equity"],
        label="Equity",
        linewidth=2,
        color="blue",
    )
    peak = np.maximum.accumulate(all_trades["equity"])
    plt.fill_between(
        all_trades["date"],
        all_trades["equity"],
        peak,
        where=all_trades["equity"] < peak,
        color="red",
        alpha=0.3,
    )
    plt.title(f"Equity Curve with Drawdowns ({tag})")
    plt.xlabel("Date")
    plt.ylabel("Equity")
    plt.legend()
    plt.savefig(chart_path)
    plt.close()

    # TXT summary
    text_path = reports_dir / f"backtest_{tag}_{timestamp}.txt"
    with open(text_path, "w", encoding="utf-8") as f:
        f.write("=== Quant Pro v16.3 Backtest Report ===\n")
        for k, v in summary.items():
            f.write(f"{k:<18}: {v:.2f}\n")
        f.write("\n--- Attribution by Symbol & Sector ---\n")
        for sym, val in attribution.items():
            sector = SECTOR_MAP.get(sym, "Unknown")
            f.write(f"{sym:<10} ({sector:<8}): {val:.2f}\n")

    logger.info("✅ Reports saved: %s, %s, %s", excel_path, chart_path, text_path)


# ==========================================================
# Main
# ==========================================================
def main() -> None:
    with open("config.yaml", "r", encoding="utf-8-sig") as f:
        cfg = yaml.safe_load(f)
    engine = TradeEngine(cfg)

    symbols = ["BTC/USDT", "ETH/USDT", "SPY"]
    all_trades, attribution = [], {}

    for sym in symbols:
        try:
            df = load_historical_data(sym)
            trades = run_backtest(engine, df, sym)
            if not trades.empty:
                all_trades.append(trades)
                attribution[sym] = trades["equity"].iloc[-1] - trades["equity"].iloc[0]
                logger.info("✅ Finished backtest for %s | Trades=%d", sym, len(trades))
            else:
                logger.warning("⚠️ No trades for %s", sym)
        except Exception as e:
            logger.error("❌ Failed backtest for %s: %s", sym, e)

    if not all_trades:
        logger.error("❌ No trades generated for any symbols")
        return

    all_trades = pd.concat(all_trades, ignore_index=True)
    start_eq, end_eq = all_trades["equity"].iloc[0], all_trades["equity"].iloc[-1]
    summary = {
        "Start Equity": start_eq,
        "End Equity": end_eq,
        "Return %": (end_eq - start_eq) / start_eq * 100,
        "Num Trades": len(all_trades),
        "Max Drawdown %": (
            (np.maximum.accumulate(all_trades["equity"]) - all_trades["equity"])
            / np.maximum.accumulate(all_trades["equity"])
        ).max()
        * 100,
    }

    save_results(all_trades, summary, attribution, tag="multi_symbol")


if __name__ == "__main__":
    main()
