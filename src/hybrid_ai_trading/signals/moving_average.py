"""
Moving Average Signal (Hybrid AI Quant Pro v22.3 – Final, 100% Coverage)
------------------------------------------------------------------------
- BUY  if short_sma > long_sma
- SELL if short_sma < long_sma
- HOLD if equal, insufficient data, invalid SMA, or errors
"""

import logging
import pandas as pd
from typing import Sequence, Mapping, Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = True


def moving_average_signal(
    bars: Sequence[Mapping[str, Any]],
    short_window: int = 5,
    long_window: int = 20,
    **kwargs
) -> str:
    if "short" in kwargs:
        short_window = kwargs["short"]
    if "long" in kwargs:
        long_window = kwargs["long"]

    if not bars or len(bars) < long_window:
        logger.info("⚠️ Not enough bars → HOLD")
        return "HOLD"

    try:
        if not all("c" in bar for bar in bars):
            logger.warning("⚠️ Missing close field → HOLD")
            return "HOLD"

        closes = [float(bar["c"]) for bar in bars]
        if any(pd.isna(v) for v in closes):
            logger.warning("⚠️ NaN detected in closes → HOLD")
            return "HOLD"

        df = pd.DataFrame({"close": closes})
        short_sma = df["close"].rolling(window=short_window).mean().iloc[-1]
        long_sma = df["close"].rolling(window=long_window).mean().iloc[-1]

        if pd.isna(short_sma) or pd.isna(long_sma):
            logger.warning("⚠️ NaN SMA → HOLD")
            return "HOLD"

        if short_sma > long_sma:
            logger.info("📈 SMA bullish crossover → BUY")
            return "BUY"
        elif short_sma < long_sma:
            logger.info("📉 SMA bearish crossover → SELL")
            return "SELL"
        else:
            logger.debug("➖ SMA equal → HOLD")
            return "HOLD"

    except Exception as e:
        logger.error(f"❌ SMA calculation failed: {e}", exc_info=True)
        return "HOLD"
