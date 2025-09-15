"""
Breakout Intraday Signal (Hybrid AI Quant Pro v22.3 – Final Polished, 100% Coverage)
-----------------------------------------------------------------------------------
- BUY  if last close >= rolling high
- SELL if last close <= rolling low
- SELL priority if price == high == low
- HOLD otherwise
- Guards: missing/invalid data, NaN, not enough bars
- Audit mode: return (decision, price, high, low)
"""

import logging
import math
from typing import List, Dict, Union, Tuple

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = True


def breakout_intraday(
    bars: List[Dict],
    window: int = 10,
    audit: bool = False
) -> Union[str, Tuple[str, float, float, float]]:
    """Return BUY/SELL/HOLD (or audit tuple) based on intraday breakout."""
    if not bars:
        logger.info("No bars → HOLD")
        return ("HOLD", math.nan, math.nan, math.nan) if audit else "HOLD"

    if window <= 0:
        logger.info("Invalid window → HOLD")
        return ("HOLD", math.nan, math.nan, math.nan) if audit else "HOLD"

    if len(bars) < window:
        logger.info("Not enough bars → HOLD")
        return ("HOLD", math.nan, math.nan, math.nan) if audit else "HOLD"

    closes = []
    for b in bars[-window:]:
        if "c" not in b:
            logger.warning("Missing close price in bar → HOLD")
            return ("HOLD", math.nan, math.nan, math.nan) if audit else "HOLD"
        try:
            closes.append(float(b["c"]))
        except Exception as e:
            logger.error(f"Failed to parse close prices: {e}")
            return ("HOLD", math.nan, math.nan, math.nan) if audit else "HOLD"

    if any(math.isnan(c) for c in closes):
        logger.warning("NaN detected in breakout_intraday closes → HOLD")
        return ("HOLD", math.nan, math.nan, math.nan) if audit else "HOLD"

    last = closes[-1]
    high = max(closes)
    low = min(closes)

    if last == high == low:
        logger.info(f"Tie case | Price={last:.2f} == High==Low → SELL")
        decision = "SELL"
    elif last >= high:
        logger.info(f"Breakout BUY: {last:.2f} >= {high:.2f}")
        decision = "BUY"
    elif last <= low:
        logger.info(f"Breakout SELL: {last:.2f} <= {low:.2f}")
        decision = "SELL"
    else:
        logger.debug(f"Inside range → HOLD | Price={last:.2f}, Low={low:.2f}, High={high:.2f}")
        decision = "HOLD"

    return (decision, last, high, low) if audit else decision
