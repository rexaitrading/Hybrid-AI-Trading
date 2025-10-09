"""
Breakout Intraday Signal (Hybrid AI Quant Pro v22.6 – Hedge-Fund OE Grade)
--------------------------------------------------------------------------
Rules:
    * BUY  if last close > rolling high
    * SELL if last close < rolling low
    * SELL priority on ties (price == high == low)
    * HOLD strictly inside range
Guards:
    * No bars
    * Invalid window
    * Not enough bars
    * Missing close field
    * Parse exception
    * NaN values
Audit=True → returns tuple (decision, price, rh, rl)
"""

import logging
import math
from typing import List, Dict, Union

# --- Helpers -----------------------------------------------------------
def make_bars(prices):
    """Utility to wrap list of closes into bar dicts with 'c' key."""
    return [{"c": p} for p in prices]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def breakout_intraday(
    bars: List[Dict[str, Union[int, float]]],
    window: int = 20,
    audit: bool = False,
) -> Union[str, tuple]:
    """Compute breakout signal with guard rails and audit mode."""
    # --- Guards ---
    if not bars:
        logger.warning("No bars provided → HOLD")
        return ("HOLD", None, None, None) if audit else "HOLD"

    if not isinstance(window, int) or window <= 0:
        logger.warning("Invalid window: %s → HOLD", window)
        return ("HOLD", None, None, None) if audit else "HOLD"

    if len(bars) < window:
        logger.info("Not enough bars: %s < %s → HOLD", len(bars), window)
        return ("HOLD", None, None, None) if audit else "HOLD"

    try:
        closes = [float(b.get("c")) for b in bars[-window:] if "c" in b]
        if len(closes) < window:
            logger.warning("Missing close fields → HOLD")
            return ("HOLD", None, None, None) if audit else "HOLD"

        # Fallback: if highs/lows missing, use closes
        highs = [float(b.get("h", b.get("c"))) for b in bars[-window:]]
        lows = [float(b.get("l", b.get("c"))) for b in bars[-window:]]

        if any(math.isnan(x) for x in closes + highs + lows):
            logger.warning("NaN detected in bars → HOLD")
            return ("HOLD", None, None, None) if audit else "HOLD"

        price = closes[-1]
        rolling_high = max(highs[:-1]) if len(highs) > 1 else highs[-1]
        rolling_low = min(lows[:-1]) if len(lows) > 1 else lows[-1]

    except Exception as e:
        logger.error("Parse exception: %s → HOLD", e)
        return ("HOLD", None, None, None) if audit else "HOLD"

    # --- Decision ---
    decision: str
    if price > rolling_high:
        decision = "BUY"
        logger.info("Breakout BUY: price=%.2f > high=%.2f", price, rolling_high)
    elif price < rolling_low:
        decision = "SELL"
        logger.info("Breakout SELL: price=%.2f < low=%.2f", price, rolling_low)
    elif price == rolling_high == rolling_low:
        decision = "SELL"  # tie → SELL priority
        logger.info("Breakout TIE → SELL priority: price=%.2f", price)
    else:
        decision = "HOLD"
        logger.debug("Inside range → HOLD: price=%.2f", price)

    return (decision, price, rolling_high, rolling_low) if audit else decision

def test_audit_tie_sell_priority():
    """Audit mode: price == high == low → SELL priority."""
    prices = [50] * 20  # tie case: all closes are equal
    decision, price, rh, rl = breakout_intraday(
        make_bars(prices), window=20, audit=True
    )
    assert decision == "SELL"  # tie → SELL priority
    assert price == rh == rl == 50.0
