"""
RSISignal (Hybrid AI Quant Pro v23.3 Ã¢â‚¬â€œ Hedge-Fund Grade, Wrapper-Aligned)
-------------------------------------------------------------------------
Logic:
- Compute RSI using WilderÃ¢â‚¬â„¢s method
- BUY if RSI < 30
- SELL if RSI > 70
- HOLD otherwise
- Guards:
  * Empty bars
  * Not enough bars
  * Missing 'c' field
  * NaN closes
  * Division by zero (loss=0)
  * NaN RSI values
- Wrapper functions for tests and pipelines
"""

import logging
from typing import Dict, List, Union

import numpy as np
import pandas as pd

logger = logging.getLogger("hybrid_ai_trading.signals.rsi_signal")


class RSISignal:
    """Relative Strength Index (RSI) trading signal generator."""

    def __init__(self, period: int = 14) -> None:
        self.period = period

    def generate(
        self, symbol: str, bars: List[Dict[str, Union[str, float]]]
    ) -> Dict[str, Union[str, float, str]]:
        """Generate RSI signal based on closing prices."""
        if not bars:
            return {"signal": "HOLD", "reason": "no bars"}

        try:
            closes = pd.Series([float(b["c"]) for b in bars if "c" in b])
        except Exception as e:
            logger.error("Ã¢ÂÅ’ Failed to parse closes for RSI: %s", e)
            return {"signal": "HOLD", "reason": "failed parse"}

        if closes.empty:
            return {"signal": "HOLD", "reason": "missing close"}

        if len(closes) < self.period + 1:
            return {"signal": "HOLD", "reason": "not enough bars"}

        if closes.isna().any():
            return {"signal": "HOLD", "reason": "nan detected"}

        # --- Price differences ---
        delta = closes.diff().to_numpy()

        # --- Gains / Losses (NumPy-safe) ---
        gains = np.clip(delta, 0, None)
        losses = np.clip(-delta, 0, None)

        try:
            avg_gain = pd.Series(gains).rolling(self.period).mean().iloc[-1]
            avg_loss = pd.Series(losses).rolling(self.period).mean().iloc[-1]
        except Exception as e:
            logger.error("Ã¢ÂÅ’ RSI calculation failed: %s", e)
            return {"signal": "HOLD", "reason": "calc failed"}

        # --- RSI calculation ---
        if avg_loss == 0:
            rsi = 100 if avg_gain > 0 else 0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        # --- Guard for NaN RSI ---
        if pd.isna(rsi):
            return {"signal": "HOLD", "reason": "nan rsi"}

        # --- Decision ---
        if rsi < 30:
            sig = "BUY"
        elif rsi > 70:
            sig = "SELL"
        else:
            sig = "HOLD"

        return {"signal": sig, "rsi": float(rsi)}


# ----------------------------------------------------------------------
# Wrappers
# ----------------------------------------------------------------------
def rsi_signal(
    bars: List[Dict[str, Union[str, float]]],
    period: int = 14,
) -> str:
    """Wrapper around RSISignal.generate. Returns only the decision string."""
    out = RSISignal(period=period).generate("SYMBOL", bars)
    return out.get("signal", "HOLD")


__all__ = ["RSISignal", "rsi_signal"]
