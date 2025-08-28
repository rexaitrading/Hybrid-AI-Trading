"""
Backtest: Breakout + Risk Manager + Black Swan Guard
Runs over historical Polygon data for each symbol in your universe.
"""

import os
import requests
import csv
from dotenv import load_dotenv
from datetime import datetime, timedelta

from src.config.settings import load_config
from src.risk.risk_manager import RiskManager
from src.risk.black_swan_guard import BlackSwanGuard

# Load env/config
load_dotenv()
cfg = load_config()
POLYGON_KEY = os.getenv("POLYGON_KEY")


def get_polygon_bars(ticker: str, start: str, end: str, limit=500):
    """Fetch daily OHLCV bars from Polygon"""
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}?limit={limit}&apiKey={POLYGON_KEY}"
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"Polygon API error {resp.status_code}: {resp.text[:200]}")
    return resp.json().get("results", [])


def breakout_signal_polygon(bars) -> str:
    """Use last 3 bars: BUY if close > max of prev 2 highs, SELL if close < min of prev 2 lows"""
    if len(bars) < 3:
        return "HOLD"
    closes = [b["c"] for b in bars]
    highs = [b["h"] for b in bars]
    lows = [b["l"] for b in bars]
    recent_close = closes[-1]
    prev_high = max(highs[:-1])
    prev_low = min(lows[:-1])
    if recent_close > prev_high:
        return "BUY"
    elif recent_close < prev_low:
        return "SELL"
    return "HOLD"


def backtest_symbol(symbol, start_date, end_date, writer=None):
    risk = RiskManager()
    guard = BlackSwanGuard()
    bars = get_polygon_bars(symbol, start_date, end_date)
    trades = 0
    pnl = 0.0

    for i in range(2, len(bars) - 1):  # need at least 3 bars and 1 for exit
        window = bars[i - 2 : i + 1]
        raw_signal = breakout_signal_polygon(window)
        guarded_signal = guard.filter_signal(raw_signal)
        final_signal = risk.control_signal(guarded_signal)

        trade_return = 0
        if final_signal == "BUY":
            entry = bars[i]["c"]  # entry price at close
            exit = bars[i + 1]["c"]  # exit at next day close
            trade_return = (exit - entry) / entry
            pnl += trade_return
            trades += 1

        elif final_signal == "SELL":
            entry = bars[i]["c"]
            exit = bars[i + 1]["c"]
            trade_return = (entry - exit) / entry  # short return
            pnl += trade_return
            trades += 1

        if writer:
            writer.writerow({
                "symbol": symbol,
                "date": datetime.fromtimestamp(bars[i]["t"]/1000).strftime("%Y-%m-%d"),
                "raw_signal": raw_signal,
                "guarded_signal": guarded_signal,
                "final_signal": final_signal,
                "trade_return": round(trade_return, 4),
                "cum_pnl": round(pnl, 4)
            })

    return trades, pnl


if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    logfile = "logs/backtest_results.csv"

    # test last 90 days
    end_date = datetime.today()
    start_date = (end_date - timedelta(days=90)).strftime("%Y-%m-%d")
    end_date = end_date.strftime("%Y-%m-%d")

    with open(logfile, "w", newline="") as f:
        fieldnames = ["symbol","date","raw_signal","guarded_signal","final_signal","trade_return","cum_pnl"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        print(f"=== BACKTEST {start_date} to {end_date} ===")
        for stock in cfg["universe"]["stocks"]:
            trades, pnl = backtest_symbol(stock, start_date, end_date, writer)
            print(f"{stock}: trades={trades}, pnl={pnl:.2%}")

    print(f"\n✅ Backtest results saved to {logfile}")
