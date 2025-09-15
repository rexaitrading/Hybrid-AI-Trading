"""
Bollinger Bands Signal (Hybrid AI Quant Pro v22.6 – Final Stable)
-----------------------------------------------------------------
- BUY  if last close < lower band
- SELL if last close > upper band
- HOLD otherwise
- Guards:
  * no bars
  * missing 'c'
  * parse error
  * NaN closes
  * invalid mean/std (NaN)
  * stdev == 0 (flat prices)
"""

import logging
import math
import statistics
from typing import List, Dict

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = True


def bollinger_bands_signal(bars: List[Dict], window: int = 20, num_std: float = 2.0) -> str:
    """Return BUY/SELL/HOLD based on Bollinger Bands."""
    if not bars:
        logger.info("No bars for Bollinger → HOLD")
        return "HOLD"

    closes = []
    for b in bars[-window:]:
        if "c" not in b:
            logger.warning("Missing 'c' in bar → HOLD")
            return "HOLD"
        try:
            closes.append(float(b["c"]))
        except Exception as e:
            logger.error(f"Failed to parse close prices: {e}")
            return "HOLD"

    if len(closes) < window:
        logger.info("Not enough bars for Bollinger → HOLD")
        return "HOLD"

    if any(math.isnan(c) for c in closes):
        logger.warning("NaN detected in Bollinger closes → HOLD")
        return "HOLD"

    mean = statistics.fmean(closes)
    stdev = statistics.pstdev(closes) if len(closes) > 1 else 0.0

    if math.isnan(mean) or math.isnan(stdev) or stdev == 0.0:
        logger.warning("Invalid mean/std in Bollinger → HOLD")
        return "HOLD"

    upper = mean + num_std * stdev
    lower = mean - num_std * stdev
    last = closes[-1]

    if last < lower:
        logger.info(f"decision=BUY | last={last:.2f}, lower={lower:.2f}, upper={upper:.2f}")
        return "BUY"
    if last > upper:
        logger.info(f"decision=SELL | last={last:.2f}, lower={lower:.2f}, upper={upper:.2f}")
        return "SELL"

    logger.debug(f"decision=HOLD | last={last:.2f}, lower={lower:.2f}, upper={upper:.2f}")
    return "HOLD"
