"""
RSI Signal (Hybrid AI Quant Pro v22.3 – Final, 100% Coverage)
-------------------------------------------------------------
- BUY  when RSI < 30
- SELL when RSI > 70
- HOLD otherwise
"""

import logging
import pandas as pd
from typing import Sequence, Mapping, Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = True


def rsi_signal(bars: Sequence[Mapping[str, Any]], period: int = 14) -> str:
    if not bars:
        logger.debug("⚠️ No bars provided → HOLD")
        return "HOLD"
    if len(bars) < period + 1:
        logger.debug(f"⚠️ Not enough bars for RSI (need {period+1}) → HOLD")
        return "HOLD"

    try:
        df = pd.DataFrame(bars)
        if "c" not in df.columns:
            logger.warning("⚠️ Missing close field → HOLD")
            return "HOLD"

        df["close"] = pd.to_numeric(df["c"], errors="coerce")
        if df["close"].isna().any():
            logger.warning("⚠️ NaN detected in closes → HOLD")
            return "HOLD"

        delta = df["close"].diff().dropna().to_list()
        if len(delta) < period:
            logger.debug("⚠️ Not enough deltas → HOLD")
            return "HOLD"

        gains = [d for d in delta[-period:] if d > 0]
        losses = [-d for d in delta[-period:] if d < 0]
        avg_gain, avg_loss = sum(gains) / period if gains else 0.0, sum(losses) / period if losses else 0.0

        if avg_loss == 0:
            if avg_gain > 0:
                logger.warning("⚠️ Loss=0 with gain → SELL fallback")
                return "SELL"
            else:
                logger.warning("⚠️ Loss=0 with no gain → BUY fallback")
                return "BUY"

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        if rsi < 30:
            logger.info(f"📉 RSI={rsi:.2f} < 30 → BUY")
            return "BUY"
        elif rsi > 70:
            logger.info(f"📈 RSI={rsi:.2f} > 70 → SELL")
            return "SELL"
        else:
            logger.debug(f"➖ RSI={rsi:.2f} inside 30-70 → HOLD")
            return "HOLD"

    except Exception as e:
        logger.error(f"❌ RSI calculation failed: {e}", exc_info=True)
        return "HOLD"
