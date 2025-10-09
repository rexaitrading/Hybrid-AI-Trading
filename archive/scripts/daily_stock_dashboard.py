"""
Daily Stock Dashboard (Hybrid AI Quant Pro v6.5 – Hedge-Fund Grade, Polished)
-----------------------------------------------------------------------------
Responsibilities:
- Fetch OHLCV bars from Polygon API
- Grade breakout signals with risk/reward logic
- Export dashboard to CSV
- Auto-execute Grade A trades via IBKR with bracket orders
"""

import csv
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

try:
    from ib_insync import IB, LimitOrder, MarketOrder, Stock, StopOrder
except ImportError:
    IB = None
    Stock = None
    MarketOrder = None
    LimitOrder = None
    StopOrder = None

# ---------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("DailyDashboard")

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------
load_dotenv()
POLYGON_KEY = os.getenv("POLYGON_KEY", "")

WATCHLIST = ["AAPL", "TSLA", "NVDA", "AMZN", "MSFT"]
LOOKBACK_DAYS = 5
CAPITAL_PER_TRADE = 10_000
STOP_PCT = 0.01
TARGET_PCT = 0.02


# ---------------------------------------------------------------------
# Data Fetcher
# ---------------------------------------------------------------------
def get_bars(symbol: str, start: str, end: str) -> List[Dict[str, Any]]:
    """Fetch OHLCV bars from Polygon.io."""
    url = (
        f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/5/minute/"
        f"{start}/{end}?limit=5000&apiKey={POLYGON_KEY}"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except requests.RequestException as e:
        logger.error("❌ Error fetching %s: %s", symbol, e)
        return []


# ---------------------------------------------------------------------
# Signal Grading
# ---------------------------------------------------------------------
def grade_stock(symbol: str, bars: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Grade a stock breakout setup with R/R evaluation."""
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
        signal, stop, target = "RANGE", None, None

    rr = 0
    if stop and target:
        upside = abs(target - last_close)
        downside = abs(last_close - stop)
        rr = upside / downside if downside > 0 else 0

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
        "grade": grade,
    }


# ---------------------------------------------------------------------
# Bracket Order Placement
# ---------------------------------------------------------------------
def place_bracket_order(ib: IB, symbol: str, info: Dict[str, Any]) -> Dict[str, Any]:
    """Send a bracket order for Grade A trades."""
    if not all([IB, Stock, MarketOrder, LimitOrder, StopOrder]):
        raise ImportError("ib_insync not available")

    qty = int(CAPITAL_PER_TRADE / info["last_close"])
    contract = Stock(symbol, "SMART", "USD")

    parent = MarketOrder("BUY", qty)
    parent.orderId = ib.client.getReqId()

    take_profit = LimitOrder("SELL", qty, round(info["target"], 2))
    take_profit.parentId = parent.orderId
    take_profit.transmit = False

    stop_loss = StopOrder("SELL", qty, round(info["stop"], 2))
    stop_loss.parentId = parent.orderId
    stop_loss.transmit = True

    ib.placeOrder(contract, parent)
    ib.placeOrder(contract, take_profit)
    ib.placeOrder(contract, stop_loss)

    logger.info(
        "🚀 Grade A TRADE PLACED | %s | Qty=%d | Stop=%.2f | Target=%.2f | R/R=%.2f",
        symbol,
        qty,
        info["stop"],
        info["target"],
        info["rr"],
    )

    return {
        "symbol": symbol,
        "qty": qty,
        "stop": round(info["stop"], 2),
        "target": round(info["target"], 2),
        "status": "AUTO_EXECUTED",
    }


# ---------------------------------------------------------------------
# Dashboard Orchestration
# ---------------------------------------------------------------------
def daily_dashboard_with_ibkr() -> None:
    """Generate daily dashboard and auto-execute Grade A trades."""
    today = datetime.today()
    start = (today - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")

    results: List[Dict[str, Any]] = []
    executed: List[Dict[str, Any]] = []

    for sym in WATCHLIST:
        bars = get_bars(sym, start, end)
        info = grade_stock(sym, bars)
        if info:
            results.append(info)

    results.sort(
        key=lambda x: (
            -1 if x["grade"] == "A" else -2 if x["grade"] == "B" else -3,
            x["rr"],
        ),
        reverse=True,
    )

    # Export to CSV
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    filename = logs_dir / f"daily_dashboard_{today.strftime('%Y%m%d')}.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "symbol",
                "grade",
                "signal",
                "last_close",
                "stop",
                "target",
                "rr",
                "status",
            ],
        )
        writer.writeheader()
        for r in results:
            status = "AUTO_EXECUTED" if r["grade"] == "A" else "LOG_ONLY"
            writer.writerow({**r, "status": status})

    logger.info("📂 Dashboard exported to %s", filename)

    # Auto-trade Grade A
    if IB:
        ib = IB()
        try:
            ib.connect("127.0.0.1", 7497, clientId=2)
            for r in results:
                if r["grade"] == "A":
                    executed.append(place_bracket_order(ib, r["symbol"], r))
        except Exception as e:  # noqa: BLE001
            logger.error("⚠️ IBKR connection failed: %s", e)
        finally:
            if ib.isConnected():
                ib.disconnect()

    if executed:
        logger.info("=== SUMMARY OF AUTO-TRADES TODAY ===")
        for e in executed:
            logger.info(
                "%s: %d shares, Stop=%.2f, Target=%.2f",
                e["symbol"],
                e["qty"],
                e["stop"],
                e["target"],
            )


if __name__ == "__main__":
    daily_dashboard_with_ibkr()
