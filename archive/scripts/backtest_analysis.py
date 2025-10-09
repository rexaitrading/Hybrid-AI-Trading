"""
Backtest Analysis (Hybrid AI Quant Pro v16.2 – Hedge-Fund OE Grade)
===================================================================
- Load event → price impact dataset (CSV or DB)
- Compute win-rates, avg returns, impact distributions
- Export quant-style charts and audit summary
"""

import os
import sqlite3
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# ------------------------------------------------------
# Logging
# ------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("BacktestAnalysis")


# ------------------------------------------------------
# Load Dataset
# ------------------------------------------------------
def load_dataset(
    source: str = "csv",
    csv_path: str = "reports/news_price_impact.csv",
    db_path: str = "data/hybrid_ai_trading.db",
) -> pd.DataFrame:
    """Load dataset from CSV or SQLite DB."""
    if source == "csv":
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV not found: {path}")
        df = pd.read_csv(path, parse_dates=["headline_time"], encoding="utf-8")
    else:
        path = Path(db_path)
        if not path.exists():
            raise FileNotFoundError(f"DB not found: {path}")
        conn = sqlite3.connect(path)
        df = pd.read_sql(
            "SELECT * FROM event_price_impact", conn, parse_dates=["headline_time"]
        )
        conn.close()

    return df


# ------------------------------------------------------
# Analysis
# ------------------------------------------------------
def analyze_dataset(df: pd.DataFrame):
    """Compute quant-style metrics on event dataset."""
    df = df.dropna(subset=["same_day_return_pct", "next_day_return_pct"]).copy()

    win_rate = (df["next_day_return_pct"] > 0).mean() * 100
    avg_same = df["same_day_return_pct"].mean()
    avg_next = df["next_day_return_pct"].mean()
    max_next = df["next_day_return_pct"].max()
    min_next = df["next_day_return_pct"].min()

    summary = {
        "Num Headlines": len(df),
        "Win Rate (Next-Day > 0)": f"{win_rate:.2f}%",
        "Avg Same-Day Return %": f"{avg_same:.3f}",
        "Avg Next-Day Return %": f"{avg_next:.3f}",
        "Max Next-Day Move %": f"{max_next:.2f}",
        "Min Next-Day Move %": f"{min_next:.2f}",
    }
    return summary, df


# ------------------------------------------------------
# Charts
# ------------------------------------------------------
def export_charts(df: pd.DataFrame, outdir: str = "reports") -> None:
    """Export histograms and equity curve."""
    Path(outdir).mkdir(parents=True, exist_ok=True)

    # Histogram
    plt.figure(figsize=(8, 5))
    df["next_day_return_pct"].hist(bins=30, color="blue", alpha=0.7)
    plt.axvline(0, color="red", linestyle="--")
    plt.title("Distribution of Next-Day Returns")
    plt.xlabel("Return %")
    plt.ylabel("Frequency")
    plt.tight_layout()
    hist_path = Path(outdir) / "hist_next_day_returns.png"
    plt.savefig(hist_path)
    plt.close()

    # Equity curve
    equity = (1 + df["next_day_return_pct"] / 100).cumprod()
    plt.figure(figsize=(8, 5))
    plt.plot(df["headline_time"], equity, color="green")
    plt.title("Equity Curve (Compounded Next-Day Returns)")
    plt.xlabel("Headline Date")
    plt.ylabel("Equity (Base=1.0)")
    plt.tight_layout()
    eq_path = Path(outdir) / "equity_curve.png"
    plt.savefig(eq_path)
    plt.close()

    logger.info("📊 Charts exported: %s, %s", hist_path, eq_path)


# ------------------------------------------------------
# Entrypoint
# ------------------------------------------------------
def main():
    df = load_dataset("csv")
    summary, df = analyze_dataset(df)

    print("\n=== Quant Backtest Report ===")
    for k, v in summary.items():
        print(f"{k:<25}: {v}")

    export_charts(df)


if __name__ == "__main__":
    main()
