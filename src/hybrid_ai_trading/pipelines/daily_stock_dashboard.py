"""
Daily Stock Dashboard (ASCII-safe)
----------------------------------
Fetch Polygon bars, grade breakouts, export CSV+JSON, optionally place IBKR bracket orders.
"""

import csv
import json
import logging

logger = logging.getLogger(__name__)
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

# Optional IBKR import (safe for tests)
try:
    from ib_insync import IB, LimitOrder, MarketOrder, Stock, StopOrder
except ImportError:
    IB = None
    Stock = None
    MarketOrder = None
    LimitOrder = None
    StopOrder = None

logger = logging.getLogger("DailyDashboard")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)

load_dotenv()
POLYGON_KEY = os.getenv("POLYGON_KEY", "")

WATCHLIST = ["AAPL", "TSLA", "NVDA", "AMZN", "MSFT"]
LOOKBACK_DAYS = 5
CAPITAL_PER_TRADE = 10_000
STOP_PCT = 0.01
TARGET_PCT = 0.02

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def get_bars(symbol: str, start: str, end: str) -> List[Dict[str, Any]]:
    """Fetch OHLCV bars from Polygon."""
    url = (
        f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/5/minute/"
        f"{start}/{end}?limit=5000&apiKey={POLYGON_KEY}"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception as e:
        logger.error("Error fetching %s: %s", symbol, e)
        return []


def grade_stock(symbol: str, bars: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Grade a stock breakout setup with risk/reward evaluation."""
    if not bars or len(bars) < 20:
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

    rr = 0.0
    if stop and target:
        upside = abs(target - last_close)
        downside = abs(last_close - stop)
        rr = upside / downside if downside > 0 else 0.0

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

    return {
        "symbol": symbol,
        "qty": qty,
        "stop": round(info["stop"], 2),
        "target": round(info["target"], 2),
        "status": "AUTO_EXECUTED",
    }


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

    # Grade priority A > B > C > PASS; then by rr
    grade_order = {"A": 3, "B": 2, "C": 1, "PASS": 0}
    results.sort(key=lambda x: (grade_order.get(x["grade"], 0), x["rr"]), reverse=True)

    if results:
        stamp = today.strftime("%Y%m%d_%H%M%S")
        csv_path = LOG_DIR / f"daily_dashboard_{stamp}.csv"
        json_path = LOG_DIR / f"daily_dashboard_{stamp}.json"

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info("Dashboard exported:\n- %s\n- %s", csv_path, json_path)

    if IB:
        ib = IB()
        try:
            ib.connect("127.0.0.1", 7497, clientId=2)
            for r in results:
                if r["grade"] == "A":
                    executed.append(place_bracket_order(ib, r["symbol"], r))
        except Exception as e:
            logger.error("IBKR connection failed: %s", e)
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
