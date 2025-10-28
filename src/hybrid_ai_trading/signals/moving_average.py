"""
MovingAverageSignal (Hybrid AI Quant Pro v2.2 – Hedge-Fund Grade)
-----------------------------------------------------------------
Responsibilities:
- Detect moving average crossovers (short vs long)
- BUY if short MA crosses above long MA
- SELL if short MA crosses below long MA
- HOLD otherwise
- Robust guards: empty bars, invalid/missing data, NaNs
- Audit-friendly structured outputs + logging
"""

import logging
from typing import Dict, List, Union

import pandas as pd

logger = logging.getLogger("hybrid_ai_trading.signals.moving_average")


class MovingAverageSignal:
    """Moving Average crossover trading signal generator."""

    def __init__(self, short_window: int = 5, long_window: int = 20) -> None:
        self.short_window = short_window
        self.long_window = long_window

    def generate(
        self, symbol: str, bars: List[Dict[str, Union[str, float]]]
    ) -> Dict[str, Union[str, float]]:
        """Generate moving average crossover signal."""
        if not bars:
            logger.info("No bars provided → HOLD (not enough bars)")
            return {"signal": "HOLD", "reason": "not enough bars"}

        if len(bars) < self.long_window + 1:
            logger.info("Not enough bars (%s) → HOLD", len(bars))
            return {"signal": "HOLD", "reason": "not enough bars"}

        try:
            closes = pd.Series([float(b["c"]) for b in bars if "c" in b])
        except Exception as e:  # noqa: BLE001
            logger.error("❌ Failed to parse closes for MA signal: %s", e)
            return {"signal": "HOLD", "reason": "failed parse"}

        if closes.empty:
            logger.warning("Missing 'c' field in bars → HOLD")
            return {"signal": "HOLD", "reason": "missing close"}

        if closes.isna().any():
            logger.warning("NaN detected in closes → HOLD")
            return {"signal": "HOLD", "reason": "nan detected"}

        try:
            short_ma = closes.rolling(self.short_window).mean()
            long_ma = closes.rolling(self.long_window).mean()
        except Exception as e:  # noqa: BLE001
            logger.error("❌ Rolling mean failed: %s", e)
            return {"signal": "HOLD", "reason": "failed rolling"}

        if pd.isna(short_ma.iloc[-1]) or pd.isna(long_ma.iloc[-1]):
            logger.warning("NaN SMA detected → HOLD")
            return {"signal": "HOLD", "reason": "nan sma"}

        prev_short, prev_long = short_ma.iloc[-2], long_ma.iloc[-2]
        curr_short, curr_long = short_ma.iloc[-1], long_ma.iloc[-1]

        if prev_short <= prev_long and curr_short > curr_long:
            logger.info("BUY signal generated (short MA crossed above long MA)")
            sig = "BUY"
        elif prev_short >= prev_long and curr_short < curr_long:
            logger.info("SELL signal generated (short MA crossed below long MA)")
            sig = "SELL"
        elif curr_short == curr_long:
            logger.info("MAs equal → HOLD")
            sig = "HOLD"
        else:
            logger.info("No crossover → HOLD")
            sig = "HOLD"

        return {"signal": sig, "short_ma": curr_short, "long_ma": curr_long}


# ----------------------------------------------------------------------
# Functional wrapper
# ----------------------------------------------------------------------
def moving_average_signal(
    bars: List[Dict[str, Union[str, float]]],
    short_window: int = 5,
    long_window: int = 20,
    **kwargs,
) -> str:
    """
    Wrapper around MovingAverageSignal.generate.
    Returns only the decision string.
    """
    out = MovingAverageSignal(short_window=short_window, long_window=long_window).generate(
        "SYMBOL", bars
    )
    return out.get("signal", "HOLD")


__all__ = ["MovingAverageSignal", "moving_average_signal"]
