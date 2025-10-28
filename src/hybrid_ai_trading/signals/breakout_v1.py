"""
BreakoutV1Signal (Hybrid AI Quant Pro v24.0 – Hedge-Fund Grade, Wrapper-Aligned)
-------------------------------------------------------------------------------
Logic:
- BUY if last close > max(highs of previous N bars)
- SELL if last close < min(lows of previous N bars)
- HOLD otherwise
- Tie case: last_close == high == low → SELL (risk-off bias)
- Guards: insufficient bars, NaN detection, parse errors
- Full audit mode with decision tuple
- breakout_v1: pure functional wrapper for tests
- breakout_signal: legacy wrapper with CoinAPI fetch
"""

import json
import logging
import math
from typing import Any, Dict, List, Tuple, Union

from hybrid_ai_trading.data.clients.coinapi_client import get_ohlcv_latest

logger = logging.getLogger("hybrid_ai_trading.signals.breakout_v1")


# ----------------------------------------------------------------------
# Internal Safe Getter
# ----------------------------------------------------------------------
def _safe_get(bar: Dict[str, Any], keys: List[str]) -> float:
    """
    Safely extract numeric values from a bar dict.
    Prevents treating 0 as falsy and raises if all keys are missing/None.
    """
    for k in keys:
        if k in bar and bar[k] is not None:
            return float(bar[k])
    raise ValueError(f"Missing required field(s): {keys}")


class BreakoutV1Signal:
    """Breakout strategy using CoinAPI OHLCV data."""

    def __init__(self, window: int = 3) -> None:
        self.window = window

    def generate(
        self,
        symbol: str,
        bars: List[Dict[str, Any]] | None = None,
        audit: bool = False,
    ) -> Union[str, Tuple[str, float, float, float]]:
        """
        Generate breakout trading signal.
        Returns str by default, or tuple in audit mode.
        """
        try:
            if bars is None:
                bars = get_ohlcv_latest(symbol, period_id="1MIN", limit=self.window)
        except Exception as e:
            logger.error("❌ Failed to fetch bars for %s: %s", symbol, e)
            self._log_decision(symbol, "HOLD", "wrapper_exception")
            return "HOLD" if not audit else ("HOLD", 0.0, 0.0, 0.0)

        if not bars or len(bars) < self.window:
            self._log_decision(symbol, "HOLD", "insufficient_data")
            return "HOLD" if not audit else ("HOLD", 0.0, 0.0, 0.0)

        try:
            closes = [_safe_get(b, ["c", "price_close"]) for b in bars]
            highs = [_safe_get(b, ["h", "price_high"]) for b in bars]
            lows = [_safe_get(b, ["l", "price_low"]) for b in bars]
        except Exception as e:
            logger.error("❌ Failed to parse bars for %s: %s", symbol, e)
            self._log_decision(symbol, "HOLD", "invalid_data")
            return "HOLD" if not audit else ("HOLD", 0.0, 0.0, 0.0)

        if any(math.isnan(x) for x in closes + highs + lows):
            logger.error("❌ NaN detected in bars for %s", symbol)
            self._log_decision(symbol, "HOLD", "nan_detected")
            return "HOLD" if not audit else ("HOLD", closes[-1], max(highs[:-1]), min(lows[:-1]))

        last_close = closes[-1]
        prev_high = max(highs[:-1])
        prev_low = min(lows[:-1])

        if last_close > prev_high:
            decision, reason = "BUY", "breakout_up"
        elif last_close < prev_low:
            decision, reason = "SELL", "breakout_down"
        elif last_close == prev_high == prev_low:
            decision, reason = "SELL", "tie_case"
        else:
            decision, reason = "HOLD", "inside_range"

        self._log_decision(symbol, decision, reason)

        if audit:
            return decision, last_close, prev_high, prev_low
        return decision

    def _log_decision(self, symbol: str, decision: str, reason: str) -> None:
        """Log structured JSON decisions for auditing."""
        payload = {"symbol": symbol, "decision": decision, "reason": reason}
        logger.info(json.dumps(payload))


# ----------------------------------------------------------------------
# Wrappers
# ----------------------------------------------------------------------
def breakout_v1(
    bars: List[Dict[str, Any]],
    window: int = 3,
    audit: bool = False,
) -> Union[str, Tuple[str, float, float, float]]:
    """Functional wrapper for injected bars (unit tests, backtests)."""
    return BreakoutV1Signal(window=window).generate(symbol="TEST", bars=bars, audit=audit)


def breakout_signal(symbol: str, window: int = 3) -> str:
    """Legacy wrapper for pipelines with live data fetch."""
    return BreakoutV1Signal(window=window).generate(symbol)


__all__ = ["BreakoutV1Signal", "breakout_v1", "breakout_signal"]
