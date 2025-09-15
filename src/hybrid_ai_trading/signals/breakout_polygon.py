"""
Breakout Strategy (Polygon Daily) – Hybrid AI Quant Pro v22.3 (Polished, 100% Coverage)
---------------------------------------------------------------------------------------
- BUY  if last close > max of previous 2 highs
- SELL if last close < min of previous 2 lows
- HOLD otherwise
- Guards: API key missing, API/network errors, malformed/incomplete/NaN bars
"""

import os
import logging
import requests
import math
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = True

load_dotenv()


def _get_polygon_key() -> Optional[str]:
    return os.getenv("POLYGON_KEY")


def get_polygon_bars(ticker: str, limit: int = 3) -> List[Dict]:
    api_key = _get_polygon_key()
    if not api_key:
        logger.warning("⚠️ POLYGON_KEY not set → returning []")
        return []

    end_date = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=90)).strftime("%Y-%m-%d")
    url = (
        f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/"
        f"1/day/{start_date}/{end_date}?limit={limit}&apiKey={api_key}"
    )

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not isinstance(results, list):
            logger.error(f"❌ Unexpected Polygon response format for {ticker}: {data}")
            return []
        return results
    except Exception as e:
        logger.error(f"❌ Polygon API error for {ticker}: {e}", exc_info=True)
        return []


def breakout_signal_polygon(ticker: str) -> str:
    try:
        bars = get_polygon_bars(ticker, limit=3)
        if len(bars) < 3:
            logger.debug(f"[{ticker}] Not enough bars → HOLD")
            return "HOLD"

        try:
            closes = [float(b.get("c")) for b in bars if b.get("c") is not None]
            highs = [float(b.get("h")) for b in bars if b.get("h") is not None]
            lows = [float(b.get("l")) for b in bars if b.get("l") is not None]
        except (ValueError, TypeError) as parse_err:
            logger.error(f"[{ticker}] ❌ Failed to parse bar values: {parse_err}")
            return "HOLD"

        if len(closes) < 3 or len(highs) < 3 or len(lows) < 3:
            logger.warning(f"[{ticker}] ⚠️ Incomplete data → HOLD")
            return "HOLD"

        recent_close, prev_high, prev_low = closes[-1], max(highs[:-1]), min(lows[:-1])

        if any(math.isnan(v) for v in [recent_close, prev_high, prev_low]):
            logger.warning(f"[{ticker}] ⚠️ NaN detected → HOLD")
            return "HOLD"

        if recent_close > prev_high:
            logger.info(f"[{ticker}] 📈 Breakout BUY: {recent_close} > {prev_high}")
            return "BUY"
        elif recent_close < prev_low:
            logger.info(f"[{ticker}] 📉 Breakout SELL: {recent_close} < {prev_low}")
            return "SELL"
        else:
            logger.debug(f"[{ticker}] ➖ HOLD {recent_close} inside [{prev_low}, {prev_high}]")
            return "HOLD"

    except Exception as e:
        logger.error(f"[{ticker}] ❌ Polygon breakout failed: {e}", exc_info=True)
        return "HOLD"
