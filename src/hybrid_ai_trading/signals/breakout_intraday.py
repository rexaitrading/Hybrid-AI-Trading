"""
Breakout Intraday Signal (Hybrid AI Quant Pro v24.1 â€“ Hedge-Fund Grade, Polished)
---------------------------------------------------------------------------------
Logic:
- BUY  if last close > max(highs) of lookback window (excluding current bar)
- SELL if last close < min(lows) of lookback window (excluding current bar)
- SELL (tie_case) if last close == high == low
- HOLD if inside range

Guards:
- no_bars
- invalid_window
- insufficient_data
- parse_error
- invalid_data (missing fields)
- nan_detected

Exports:
- BreakoutIntradaySignal (class)
- breakout_intraday (wrapper with audit mode)
"""

import logging
import math
from typing import Any, Dict, List, Tuple, Union

logger = logging.getLogger("hybrid_ai_trading.signals.breakout_intraday")


class BreakoutIntradaySignal:
    """Intraday breakout detector with configurable lookback window."""

    def __init__(self, lookback: int = 5) -> None:
        self.lookback = lookback

    def generate(self, symbol: str, bars: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate breakout signal from bar data with audit-friendly reasons."""
        if not bars:
            logger.info("No bars provided â†’ HOLD")
            return {"symbol": symbol, "signal": "HOLD", "reason": "no_bars"}

        if self.lookback <= 0:
            logger.info("Invalid window (<=0) â†’ HOLD")
            return {"symbol": symbol, "signal": "HOLD", "reason": "invalid_window"}

        if len(bars) < self.lookback:
            logger.info("Not enough bars â†’ HOLD")
            return {"symbol": symbol, "signal": "HOLD", "reason": "insufficient_data"}

        try:
            closes = [float(b.get("c")) for b in bars if "c" in b]
            highs = [float(b.get("h")) for b in bars if "h" in b]
            lows = [float(b.get("l")) for b in bars if "l" in b]
        except Exception as e:  # noqa: BLE001
            logger.error("âŒ Failed to parse bar data: %s", e)
            return {"symbol": symbol, "signal": "HOLD", "reason": "parse_error"}

        if (
            len(closes) < self.lookback
            or len(highs) < self.lookback
            or len(lows) < self.lookback
        ):
            logger.warning("Missing c/h/l fields â†’ HOLD")
            return {"symbol": symbol, "signal": "HOLD", "reason": "invalid_data"}

        if any(math.isnan(x) for x in closes + highs + lows):
            logger.warning("NaN detected â†’ HOLD")
            return {"symbol": symbol, "signal": "HOLD", "reason": "nan_detected"}

        # Last close vs. prior highs/lows (exclude the current bar)
        window_closes = closes[-self.lookback :]
        window_highs = highs[-self.lookback : -1]
        window_lows = lows[-self.lookback : -1]

        last_close = window_closes[-1]
        high = max(window_highs) if window_highs else last_close
        low = min(window_lows) if window_lows else last_close

        if last_close > high:
            logger.info("Breakout UP detected")
            return {"symbol": symbol, "signal": "BUY", "reason": "breakout_up"}
        if last_close < low:
            logger.info("Breakout DOWN detected")
            return {"symbol": symbol, "signal": "SELL", "reason": "breakout_down"}
        if high == low == last_close:
            logger.info("Tie case (flat range) â†’ SELL")
            return {"symbol": symbol, "signal": "SELL", "reason": "tie_case"}

        logger.debug("Inside range â†’ HOLD")
        return {"symbol": symbol, "signal": "HOLD", "reason": "inside_range"}


# ----------------------------------------------------------------------
# Functional wrapper (audit + non-audit modes)
# ----------------------------------------------------------------------
def breakout_intraday(
    bars: List[Dict[str, Any]],
    window: int = 5,
    audit: bool = False,
) -> Union[str, Tuple[str, float, float, float]]:
    """
    Functional wrapper around BreakoutIntradaySignal.

    Args:
        bars: list of bar dicts with 'c','h','l'
        window: lookback period
        audit: if True, return (decision, close, high, low)

    Returns:
        str (BUY/SELL/HOLD) or tuple in audit mode
    """
    signal = BreakoutIntradaySignal(lookback=window).generate("SYMBOL", bars)

    decision = signal.get("signal", "HOLD")
    last_close = float(bars[-1].get("c", 0.0)) if bars else 0.0
    high = (
        float(max([b.get("h", 0.0) for b in bars[-window:-1]], default=last_close))
        if bars
        else 0.0
    )
    low = (
        float(min([b.get("l", 0.0) for b in bars[-window:-1]], default=last_close))
        if bars
        else 0.0
    )

    if audit:
        return decision, last_close, high, low
    return decision


__all__ = ["BreakoutIntradaySignal", "breakout_intraday"]
