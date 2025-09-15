"""
Breakout v1 Signal (Hybrid AI Quant Pro – v22.4 AAA Polished & 100% Coverage)
------------------------------------------------------------------------------
Rules:
- BUY  if last close > prior rolling high
- SELL if last close < prior rolling low
- SELL priority if price == high == low (flat window)
- HOLD if last close == rolling high or == rolling low (false breakout / retest)
- HOLD if strictly inside range

Guards:
- No bars
- Invalid window
- Not enough bars
- NaN values
- Parse errors (ValueError, TypeError, RuntimeError)

Audit Mode:
- Returns tuple (decision, price, rolling_high, rolling_low)

Wrapper breakout_signal:
- bars=None → fetches via get_ohlcv_latest
- Invalid bar format handled safely
- Exception during fetch logged & returns HOLD
"""

import logging
import math
from typing import List, Dict, Union, Tuple

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

__all__ = ["get_ohlcv_latest", "breakout_v1", "breakout_signal"]

# --------------------------------------------------------------------
# Stub fetcher (monkeypatched in tests)
# --------------------------------------------------------------------
def get_ohlcv_latest(symbol: str, limit: int = 50) -> List[Dict]:
    """Stub for OHLCV fetch (monkeypatched in tests)."""
    logger.warning("⚠️ get_ohlcv_latest is a placeholder, returning empty list")
    return []

# --------------------------------------------------------------------
# Core breakout detection
# --------------------------------------------------------------------
def breakout_v1(
    bars: List[Dict],
    window: int = 3,
    audit: bool = False
) -> Union[str, Tuple[str, float, float, float]]:
    """Core breakout/breakdown detection logic with audit mode."""

    # --- Guard: no bars ---
    if not bars:
        logger.info("No bars → HOLD")
        return ("HOLD", math.nan, math.nan, math.nan) if audit else "HOLD"

    # --- Guard: invalid window ---
    if window <= 0:
        logger.info("Invalid window → HOLD")
        return ("HOLD", math.nan, math.nan, math.nan) if audit else "HOLD"

    # --- Guard: not enough bars ---
    if len(bars) < window:
        logger.info("Not enough bars → HOLD")
        return ("HOLD", math.nan, math.nan, math.nan) if audit else "HOLD"

    # --- Parse closes ---
    try:
        closes = [float(b.get("c", math.nan)) for b in bars]
    except Exception as e:
        logger.error(f"❌ Failed to parse close prices: {e}")
        return ("HOLD", math.nan, math.nan, math.nan) if audit else "HOLD"

    price = closes[-1]

    # --- Edge case: window=1 ---
    if window == 1:
        logger.info("Window=1 edge case → HOLD")
        return ("HOLD", price, math.nan, math.nan) if audit else "HOLD"

    prior_closes = closes[-window:-1]  # exclude last bar
    rolling_high = max(prior_closes)
    rolling_low = min(prior_closes)

    # --- NaN check ---
    if any(math.isnan(v) for v in [price, rolling_high, rolling_low]):
        logger.warning("⚠️ NaN detected in values → HOLD")
        return ("HOLD", price, rolling_high, rolling_low) if audit else "HOLD"

    # --- Decision rules ---
    if price == rolling_high == rolling_low:
        decision = "SELL"
        logger.info(f"Tie case → SELL (price={price})")
    elif price < rolling_low:
        decision = "SELL"
        logger.info(f"Breakdown SELL {price:.2f} < {rolling_low:.2f}")
    elif price > rolling_high:
        decision = "BUY"
        logger.info(f"Breakout BUY {price:.2f} > {rolling_high:.2f}")
    elif price == rolling_low or price == rolling_high:
        decision = "HOLD"
        logger.info(f"Retest HOLD @ {price:.2f}")
    else:
        decision = "HOLD"
        logger.debug(
            f"Inside range HOLD | Low={rolling_low:.2f}, Price={price:.2f}, High={rolling_high:.2f}"
        )

    return (decision, price, rolling_high, rolling_low) if audit else decision

# --------------------------------------------------------------------
# Wrapper
# --------------------------------------------------------------------
def breakout_signal(symbol: str, bars: List[Dict] = None) -> str:
    """Production/demo wrapper for breakout_v1."""
    if bars is None:
        try:
            bars = get_ohlcv_latest(symbol, limit=50)
        except Exception as e:
            logger.error(f"❌ Data fetch failed: {e}")
            return "HOLD"

    if not bars:
        return "HOLD"

    converted: List[Dict[str, float]] = []
    for b in bars:
        try:
            if "c" in b:
                converted.append({"c": float(b["c"])})
            elif "price_close" in b:
                converted.append({"c": float(b["price_close"])})
            else:
                logger.error("❌ Invalid bar format in breakout_signal")
                return "HOLD"
        except Exception as e:
            logger.error(f"❌ Error parsing bar {b}: {e}")
            return "HOLD"

    return breakout_v1(converted, window=3, audit=False)
