"""
Quant Pro v4.0 Backtest Harness (Final)
---------------------------------------
- Runs multi-symbol historical backtests using TradeEngine
- Loads OHLCV data from /data/*.csv
- Simple example strategy: MA20 trend-following
- Exports results: Excel, PNG chart, TXT summary
- Attribution by symbol + sector
"""

import os, sys, yaml, pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

# 🔑 Ensure src/ is on Python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from hybrid_ai_trading.trade_engine import TradeEngine

# ------------------------------------------------------
# Sector Map for Attribution
# ------------------------------------------------------
SECTOR_MAP = {
    "BTC/USDT": "Crypto",
    "ETH/USDT": "Crypto",
    "SPY": "Equities",
}

# ------------------------------------------------------
# Load Historical Data
# ------------------------------------------------------
def load_historical_data(symbol: str) -> pd.DataFrame:
    """Load OHLCV data from data/ folder (CSV)."""
    fname = f"data/{symbol.replace('/', '_')}.csv"
    if not os.path.exists(fname):
        raise FileNotFoundError(f"No data file for {symbol}. Expected {fname}")
    return pd.read_csv(fname, parse_dates=["date"])

# ------------------------------------------------------
# Backtest Runner
# ------------------------------------------------------
def run_backtest(engine, data: pd.DataFrame, symbol: str):
    """Run backtest for one symbol using a MA20 crossover strategy."""
    trades = []
    data["MA20"] = data["close"].rolling(20).mean()

    for _, row in data.iterrows():
        price = row["close"]
        signal = "HOLD"

        if row["close"] > row["MA20"]:
            signal = "BUY"
        elif row["close"] < row["MA20"]:
            signal = "SELL"

        result = engine.process_signal(symbol, signal, size=1, price=price)
        engine.portfolio.update_equity({symbol: price})

        trades.append({
            "date": row["date"],
            "symbol": symbol,
            "signal": signal,
            "price": price,
            "status": result["status"],
            "equity": engine.get_equity(),
        })

    return pd.DataFrame(trades)

# ------------------------------------------------------
# Save Results
# ------------------------------------------------------
def save_results(all_trades: pd.DataFrame, summary: dict, attribution: dict, tag="multi"):
    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Excel
    excel_path = os.path.join(reports_dir, f"backtest_{tag}_{timestamp}.xlsx")
    with pd.ExcelWriter(excel_path, engine="xlsxwriter") as writer:
        all_trades.to_excel(writer, sheet_name="Trades", index=False)

        eq = all_trades[["date", "equity"]]
        eq.to_excel(writer, sheet_name="EquityCurve", index=False)

        pd.DataFrame.from_dict(summary, orient="index", columns=["Value"]).to_excel(writer, sheet_name="Summary")
        pd.DataFrame.from_dict(attribution, orient="index", columns=["PnL"]).to_excel(writer, sheet_name="Attribution")

    # PNG Equity Curve
    plt.figure(figsize=(12, 6))
    plt.plot(all_trades["date"], all_trades["equity"], label="Equity Curve", linewidth=2, color="blue")
    peak = np.maximum.accumulate(all_trades["equity"])
    dd = (peak - all_trades["equity"]) / peak
    plt.fill_between(all_trades["date"], all_trades["equity"], peak, where=all_trades["equity"] < peak, color="red", alpha=0.3)
    plt.title(f"Equity Curve with Drawdowns ({tag})")
    plt.xlabel("Date")
    plt.ylabel("Equity")
    plt.legend()
    chart_path = os.path.join(reports_dir, f"backtest_{tag}_{timestamp}.png")
    plt.savefig(chart_path)
    plt.close()

    # TXT summary
    text_path = os.path.join(reports_dir, f"backtest_{tag}_{timestamp}.txt")
    with open(text_path, "w") as f:
        f.write("=== Quant Pro v4.0 Backtest Report ===\n")
        for k, v in summary.items():
            f.write(f"{k:<18}: {v:.2f}\n")
        f.write("\n--- Attribution by Symbol ---\n")
        for sym, val in attribution.items():
            f.write(f"{sym:<10}: {val:.2f}\n")
        f.write("===============================\n")

    print(f"\n✅ Backtest reports saved:\n- {excel_path}\n- {chart_path}\n- {text_path}")

# ------------------------------------------------------
# Main
# ------------------------------------------------------
def main():
    # Load config
    with open("config.yaml", "r", encoding="utf-8-sig") as f:
        cfg = yaml.safe_load(f)
    engine = TradeEngine(cfg)

    symbols = ["BTC/USDT", "ETH/USDT", "SPY"]
    all_trades = []
    attribution = {}

    for sym in symbols:
        df = load_historical_data(sym)
        trades = run_backtest(engine, df, sym)
        all_trades.append(trades)

        # Attribution = last equity - first equity (per symbol)
        if not trades.empty:
            attribution[sym] = trades["equity"].iloc[-1] - trades["equity"].iloc[0]

    all_trades = pd.concat(all_trades)

    # Summary
    summary = {
        "Start Equity": all_trades["equity"].iloc[0],
        "End Equity": all_trades["equity"].iloc[-1],
        "Return %": (all_trades["equity"].iloc[-1] - all_trades["equity"].iloc[0]) / all_trades["equity"].iloc[0] * 100,
        "Num Trades": len(all_trades),
        "Max Drawdown %": max(0, ((np.maximum.accumulate(all_trades["equity"]) - all_trades["equity"]) / np.maximum.accumulate(all_trades["equity"])).max()) * 100,
    }

    save_results(all_trades, summary, attribution, tag="multi_symbol")

if __name__ == "__main__":
    main()
