"""
MACD Signal (Hybrid AI Quant Pro v22.3 – Final, 100% Coverage)
--------------------------------------------------------------
- BUY  when MACD > Signal
- SELL when MACD < Signal
- HOLD when equal, insufficient data, missing fields, or errors
"""

import logging
import pandas as pd
from typing import Sequence, Mapping, Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = True


def macd_signal(bars: Sequence[Mapping[str, Any]], short: int = 12, long: int = 26, signal: int = 9) -> str:
    if not bars:
        logger.debug("⚠️ No bars provided → HOLD")
        return "HOLD"

    if len(bars) < long + signal:
        logger.debug(f"⚠️ Not enough bars for MACD (need {long+signal}) → HOLD")
        return "HOLD"

    try:
        df = pd.DataFrame(bars)
        if "c" not in df.columns:
            logger.warning("⚠️ Missing close field in bars → HOLD")
            return "HOLD"

        df["close"] = pd.to_numeric(df["c"], errors="coerce")
        if df["close"].isna().any():
            logger.warning("⚠️ NaN detected in close prices → HOLD")
            return "HOLD"

        short_ema = df["close"].ewm(span=short, adjust=False).mean()
        long_ema = df["close"].ewm(span=long, adjust=False).mean()
        macd = short_ema - long_ema
        signal_line = macd.ewm(span=signal, adjust=False).mean()

        macd_val, signal_val = macd.iloc[-1], signal_line.iloc[-1]
        if pd.isna(macd_val) or pd.isna(signal_val):
            logger.warning("⚠️ NaN MACD/Signal → HOLD")
            return "HOLD"

        if macd_val > signal_val:
            logger.info(f"📈 MACD BUY | {macd_val:.4f} > {signal_val:.4f}")
            return "BUY"
        elif macd_val < signal_val:
            logger.info(f"📉 MACD SELL | {macd_val:.4f} < {signal_val:.4f}")
            return "SELL"
        else:
            logger.debug(f"➖ MACD equals Signal ({macd_val:.4f}) → HOLD")
            return "HOLD"

    except Exception as e:
        logger.error(f"❌ MACD calculation failed: {e}", exc_info=True)
        return "HOLD"
