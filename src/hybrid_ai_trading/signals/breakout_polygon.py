"""
BreakoutPolygonSignal (Hybrid AI Quant Pro v23.6 Ã¢â‚¬â€œ OE AAA Polished)
-------------------------------------------------------------------
- BUY if last close > max of prev highs
- SELL if last close < min of prev lows
- HOLD otherwise
Wrappers:
- BreakoutPolygonSignal class
- breakout_signal_polygon(symbol): functional wrapper
"""

import logging
import math
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)
try:
    from dotenv import load_dotenv  # optional

except Exception:
    # no-op if dotenv is missing or misconfigured
    def load_dotenv(*args, **kwargs):
        return None


class PolygonAPIError(RuntimeError):
    """Raised for Polygon API request or response errors."""


class BreakoutPolygonSignal:
    def __init__(
        self, api_key: Optional[str] = None, lookback: int = 3, min_bars: int = 3
    ):
        self.api_key = api_key or os.getenv("POLYGON_KEY")
        self.lookback = lookback
        self.min_bars = min_bars
        if not self.api_key:
            logger.warning("Ã¢Å¡Â Ã¯Â¸Â POLYGON_KEY not set. API calls will fail.")

    def _get_polygon_bars(self, ticker: str, limit: int = 3) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []
        end = datetime.today().strftime("%Y-%m-%d")
        start = (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")
        url = (
            f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/"
            f"1/day/{start}/{end}?limit={limit}&apiKey={self.api_key}"
        )
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                raise PolygonAPIError(
                    f"Polygon API error {resp.status_code}: {resp.text[:200]}"
                )
            data = resp.json().get("results", [])
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error("Ã¢ÂÅ’ Polygon request failed: %s", e)
            return []

    def generate(
        self, ticker: str, bars: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        try:
            bars = (
                bars
                if bars is not None
                else self._get_polygon_bars(ticker, limit=self.lookback)
            )
            if len(bars) < self.min_bars:
                return {"signal": "HOLD", "reason": "not_enough_bars"}

            try:
                closes = [float(b["c"]) for b in bars if "c" in b]
                highs = [float(b["h"]) for b in bars if "h" in b]
                lows = [float(b["l"]) for b in bars if "l" in b]
            except Exception as e:
                logger.error("Ã¢ÂÅ’ Failed to parse bar data: %s", e)
                return {"signal": "HOLD", "reason": "parse_error"}

            if (
                len(closes) < self.min_bars
                or len(highs) < self.min_bars
                or len(lows) < self.min_bars
            ):
                return {"signal": "HOLD", "reason": "incomplete_data"}
            if any(math.isnan(x) for x in closes + highs + lows):
                return {"signal": "HOLD", "reason": "nan_detected"}

            recent_close = closes[-1]
            prev_high = max(highs[:-1])
            prev_low = min(lows[:-1])

            if recent_close > prev_high:
                return {"signal": "BUY", "reason": "breakout_up"}
            if recent_close < prev_low:
                return {"signal": "SELL", "reason": "breakout_down"}
            return {"signal": "HOLD", "reason": "inside_range"}
        except Exception as e:
            logger.error("Ã¢ÂÅ’ BreakoutPolygonSignal outermost failure: %s", e)
            return {"signal": "HOLD", "reason": "exception"}


# ------------------ Functional Wrapper ------------------
def breakout_signal_polygon(symbol: str, lookback: int = 3) -> str:
    """Wrapper for pipelines/tests."""
    sig = BreakoutPolygonSignal(lookback=lookback)
    result = sig.generate(symbol)
    return result.get("signal", "HOLD")


__all__ = ["BreakoutPolygonSignal", "PolygonAPIError", "breakout_signal_polygon"]
