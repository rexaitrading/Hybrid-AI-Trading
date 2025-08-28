import os
import requests
from dotenv import load_dotenv

load_dotenv()
POLYGON_KEY = os.getenv("POLYGON_KEY")


def get_polygon_bars(ticker: str, limit: int = 3):
    """Fetch last N daily bars from Polygon"""
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/2024-01-01/2025-01-01?limit={limit}&apiKey={POLYGON_KEY}"
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"Polygon API error {resp.status_code}: {resp.text[:200]}")
    return resp.json().get("results", [])


def breakout_signal_polygon(ticker: str) -> str:
    """
    Breakout strategy using last 3 bars:
    - BUY if last close > max of previous 2 highs
    - SELL if last close < min of previous 2 lows
    - else HOLD
    """
    bars = get_polygon_bars(ticker, limit=3)
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
    else:
        return "HOLD"
