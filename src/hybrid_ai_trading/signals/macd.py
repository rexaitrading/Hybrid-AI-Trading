"""
MACDSignal (Hybrid AI Quant Pro v2.3 – Hedge-Fund Grade, Test-Aligned)
----------------------------------------------------------------------
Responsibilities:
- Compute MACD (EMA12 – EMA26) and Signal line (EMA9 of MACD)
- Detect crossovers:
  * BUY  if MACD crosses above Signal OR stays above in uptrend
  * SELL if MACD crosses below Signal OR stays below in downtrend
  * HOLD otherwise
- Robust guards: no bars, insufficient bars, invalid/missing data, NaNs
- Audit-friendly structured outputs + logging
"""

import logging
import math
from typing import Dict, List, Union

import pandas as pd

logger = logging.getLogger("hybrid_ai_trading.signals.macd")


class MACDSignal:
    """Moving Average Convergence Divergence (MACD) signal generator."""

    def __init__(self, fast: int = 12, slow: int = 26, signal_window: int = 9) -> None:
        self.fast = fast
        self.slow = slow
        self.signal_window = signal_window

    def generate(self, symbol: str, bars: List[Dict[str, float]]) -> Dict[str, Union[str, float]]:
        """Generate a MACD signal from bars with close 'c'."""
        if not bars:
            logger.info("No bars provided → HOLD")
            return {"signal": "HOLD", "reason": "no bars"}

        try:
            closes = pd.Series([float(b["c"]) for b in bars if "c" in b])
        except Exception as e:
            logger.error("Invalid bar format for MACD: %s", e)
            return {"signal": "HOLD", "reason": "invalid"}

        if closes.empty:
            logger.error("Invalid: no 'c' fields found in bars → HOLD")
            return {"signal": "HOLD", "reason": "invalid"}

        if len(closes) < self.slow + self.signal_window:
            logger.info("Not enough bars (%s) → HOLD", len(closes))
            return {"signal": "HOLD", "reason": "not enough bars"}

        if closes.isna().any():
            logger.warning("NaN detected in closes → HOLD")
            return {"signal": "HOLD", "reason": "nan detected"}

        ema_fast = closes.ewm(span=self.fast, adjust=False).mean()
        ema_slow = closes.ewm(span=self.slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=self.signal_window, adjust=False).mean()
        histogram = macd - signal_line

        if math.isnan(macd.iloc[-1]) or math.isnan(signal_line.iloc[-1]):
            logger.warning("NaN MACD/Signal value detected → HOLD")
            return {"signal": "HOLD", "reason": "nan macd"}

        # --- Decision Logic ---
        if macd.iloc[-2] < signal_line.iloc[-2] and macd.iloc[-1] > signal_line.iloc[-1]:
            logger.info("MACD crossover up → BUY")
            sig = "BUY"
        elif macd.iloc[-2] > signal_line.iloc[-2] and macd.iloc[-1] < signal_line.iloc[-1]:
            logger.info("MACD crossover down → SELL")
            sig = "SELL"
        elif macd.iloc[-1] > signal_line.iloc[-1]:
            logger.info("MACD above signal → BUY (trend confirmation)")
            sig = "BUY"
        elif macd.iloc[-1] < signal_line.iloc[-1]:
            logger.info("MACD below signal → SELL (trend confirmation)")
            sig = "SELL"
        else:
            logger.info("MACD holds inside range → HOLD")
            sig = "HOLD"

        return {
            "signal": sig,
            "macd": float(macd.iloc[-1]),
            "signal_line": float(signal_line.iloc[-1]),
            "histogram": float(histogram.iloc[-1]),
        }


def macd_signal(
    bars: List[Dict[str, float]],
    fast: int = 12,
    slow: int = 26,
    signal_window: int = 9,
) -> str:
    """Wrapper around MACDSignal.generate. Returns only the decision string."""
    out = MACDSignal(fast=fast, slow=slow, signal_window=signal_window).generate("SYMBOL", bars)
    return out.get("signal", "HOLD")


__all__ = ["MACDSignal", "macd_signal"]
