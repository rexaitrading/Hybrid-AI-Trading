"""
Backtest Analysis for Hybrid AI Trading System (Quant Pro v6.0)
---------------------------------------------------------------
- Load event → price impact dataset (CSV or DB)
- Compute win-rates, avg returns, impact distributions
- Export quant-style charts and summary report
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import sqlite3


def load_dataset(source="csv", csv_path="reports/news_price_impact.csv",
                 db_path="data/hybrid_ai_trading.db"):
    """Load dataset from CSV or SQLite DB."""
    if source == "csv":
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV not found: {csv_path}")
        df = pd.read_csv(csv_path, parse_dates=["headline_time"], encoding="utf-8")
    else:
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"DB not found: {db_path}")
        conn = sqlite3.connect(db_path)
        df = pd.read_sql("SELECT * FROM event_price_impact", conn,
                         parse_dates=["headline_time"])
        conn.close()

    return df


def analyze_dataset(df: pd.DataFrame):
    """Compute quant-style metrics on event dataset."""
    df = df.dropna(subset=["same_day_return_pct", "next_day_return_pct"]).copy()

    # Metrics
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


def export_charts(df: pd.DataFrame, outdir="reports"):
    """Export histograms and equity curve."""
    os.makedirs(outdir, exist_ok=True)

    # Histogram of next-day returns
    plt.figure(figsize=(8, 5))
    df["next_day_return_pct"].hist(bins=30, color="blue", alpha=0.7)
    plt.axvline(0, color="red", linestyle="--")
    plt.title("Distribution of Next-Day Returns")
    plt.xlabel("Return %")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "hist_next_day_returns.png"))
    plt.close()

    # Equity curve (compounding returns)
    equity = (1 + df["next_day_return_pct"] / 100).cumprod()
    plt.figure(figsize=(8, 5))
    plt.plot(df["headline_time"], equity, color="green")
    plt.title("Equity Curve (Compounded on Next-Day Returns)")
    plt.xlabel("Headline Date")
    plt.ylabel("Equity (Base=1.0)")
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "equity_curve.png"))
    plt.close()

    print(f"📊 Charts exported to {outdir}/")


def main():
    # Load dataset
    df = load_dataset(source="csv")

    # Analyze
    summary, df = analyze_dataset(df)

    print("\n=== Quant Backtest Report ===")
    for k, v in summary.items():
        print(f"{k:<25}: {v}")

    # Export charts
    export_charts(df)


if __name__ == "__main__":
    main()
