import os, requests, csv
from dotenv import load_dotenv
from datetime import datetime, timedelta
from ib_insync import *

load_dotenv()
POLYGON_KEY = os.getenv("POLYGON_KEY")

# === CONFIG ===
WATCHLIST = ["AAPL", "TSLA", "NVDA", "AMZN", "MSFT"]
LOOKBACK_DAYS = 5
CAPITAL_PER_TRADE = 10000  # USD allocation per trade
STOP_PCT = 0.01            # 1% stop loss
TARGET_PCT = 0.02          # 2% profit target

def get_bars(symbol, start, end, interval="5", timespan="minute"):
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{interval}/{timespan}/{start}/{end}?limit=5000&apiKey={POLYGON_KEY}"
    resp = requests.get(url)
    if resp.status_code != 200:
        print(f"Error fetching {symbol}: {resp.text[:200]}")
        return []
    return resp.json().get("results", [])

def grade_stock(symbol, bars):
    if len(bars) < 20:
        return None

    closes = [b["c"] for b in bars]
    highs = [b["h"] for b in bars]
    lows = [b["l"] for b in bars]

    last_close = closes[-1]
    recent_high = max(highs[-11:-1])
    recent_low = min(lows[-11:-1])

    if last_close > recent_high:
        signal = "BREAKOUT UP"
        stop = last_close * (1 - STOP_PCT)
        target = last_close * (1 + TARGET_PCT)
    elif last_close < recent_low:
        signal = "BREAKOUT DOWN"
        stop = last_close * (1 + STOP_PCT)
        target = last_close * (1 - TARGET_PCT)
    else:
        signal = "RANGE"
        stop, target = None, None

    if stop and target:
        upside = abs(target - last_close)
        downside = abs(last_close - stop)
        rr = upside / downside if downside > 0 else 0
    else:
        rr = 0

    if rr >= 2.0:
        grade = "A"
    elif rr >= 1.5:
        grade = "B"
    elif rr > 1.0:
        grade = "C"
    else:
        grade = "PASS"

    return {
        "symbol": symbol,
        "signal": signal,
        "last_close": last_close,
        "stop": stop,
        "target": target,
        "rr": rr,
        "grade": grade
    }

def place_bracket_order(ib, symbol, info):
    """Send a bracket order for Grade A trades"""
    qty = int(CAPITAL_PER_TRADE / info["last_close"])
    contract = Stock(symbol, 'SMART', 'USD')

    # Parent order
    parent = MarketOrder('BUY', qty)
    parent.orderId = ib.client.getReqId()

    # Take profit
    takeProfit = LimitOrder('SELL', qty, round(info["target"], 2))
    takeProfit.parentId = parent.orderId
    takeProfit.transmit = False

    # Stop loss
    stopLoss = StopOrder('SELL', qty, round(info["stop"], 2))
    stopLoss.parentId = parent.orderId
    stopLoss.transmit = True

    # Place orders
    ib.placeOrder(contract, parent)
    ib.placeOrder(contract, takeProfit)
    ib.placeOrder(contract, stopLoss)

    print("="*60)
    print(f"🚀 Grade A TRADE PLACED on {symbol}")
    print(f"   Quantity: {qty}")
    print(f"   Stop: {info['stop']:.2f}")
    print(f"   Target: {info['target']:.2f}")
    print(f"   Risk/Reward: {info['rr']:.2f}")
    print("   ✅ Bracket order sent to IBKR Paper")
    print("="*60)

    return {
        "symbol": symbol,
        "qty": qty,
        "stop": round(info["stop"], 2),
        "target": round(info["target"], 2),
        "status": "AUTO_EXECUTED"
    }

def daily_dashboard_with_ibkr():
    today = datetime.today()
    start = (today - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")

    results = []
    executed = []  # track auto trades

    for sym in WATCHLIST:
        bars = get_bars(sym, start, end)
        info = grade_stock(sym, bars)
        if info:
            results.append(info)

    results.sort(key=lambda x: (-1 if x["grade"]=="A" else -2 if x["grade"]=="B" else -3, x["rr"]), reverse=True)

    # === PRINT DASHBOARD ===
    print("\n=== DAILY STOCK DASHBOARD ===")
    for r in results:
        stop_str = f"{r['stop']:.2f}" if r['stop'] else "-"
        tgt_str = f"{r['target']:.2f}" if r['target'] else "-"
        print(f"{r['symbol']:5} | Grade {r['grade']} | {r['signal']:<12} | "
              f"Last {r['last_close']:.2f} | Stop {stop_str} | Target {tgt_str} | R/R {r['rr']:.2f}")

    # === EXPORT TO CSV ===
    os.makedirs("logs", exist_ok=True)
    filename = f"logs/daily_dashboard_{today.strftime('%Y%m%d')}.csv"
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["symbol","grade","signal","last_close","stop","target","rr","status"])
        writer.writeheader()
        for r in results:
            status = "AUTO_EXECUTED" if r["grade"]=="A" else "LOG_ONLY"
            writer.writerow({**r, "status": status})

    print(f"\n✅ Dashboard exported to {filename}")

    # === AUTO-TRADE GRADE A ONLY ===
    ib = IB()
    try:
        ib.connect('127.0.0.1', 7497, clientId=2)
        for r in results:
            if r["grade"] == "A":
                trade_info = place_bracket_order(ib, r["symbol"], r)
                executed.append(trade_info)
            elif r["grade"] == "B":
                print(f"📌 Grade B candidate logged only: {r['symbol']} (R/R {r['rr']:.2f})")
    except Exception as e:
        print("⚠️ IBKR connection failed:", e)
    finally:
        if ib.isConnected():
            ib.disconnect()

    if executed:
        print("\n=== SUMMARY OF AUTO-TRADES TODAY ===")
        for e in executed:
            print(f" {e['symbol']}: {e['qty']} shares, Stop {e['stop']}, Target {e['target']}")

if __name__ == "__main__":
    daily_dashboard_with_ibkr()
