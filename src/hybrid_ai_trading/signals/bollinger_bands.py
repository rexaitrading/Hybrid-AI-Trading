"""
Bollinger Bands Signal (Hybrid AI Quant Pro – Hedge Fund Grade v24.0)
---------------------------------------------------------------------
Logic:
- Uses SMA ± (N * stdev) bands (default: 20-period SMA, 2.0 stdev).
- BUY  if last close < lower band (oversold).
- SELL if last close > upper band (overbought).
- HOLD otherwise.

Guards:
- Empty or insufficient bars → HOLD
- Missing close field(s) → HOLD + WARNING
- NaN values → HOLD + WARNING
- Parse errors (statistics failure) → HOLD + ERROR
- Flat stdev → HOLD

Exports:
- BollingerBandsSignal (class)
- bollinger_bands_signal (wrapper for tests & legacy code)
"""

import logging
import math
import statistics
from typing import Any, Union

logger = logging.getLogger("hybrid_ai_trading.signals.bollinger_bands")


class BollingerBandsSignal:
    """Generate Bollinger Bands trading signals."""

    def __init__(self, period: int = 20, std_dev: float = 2.0) -> None:
        self.period = period
        self.std_dev = std_dev

    def generate(self, symbol: str, bars: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate a Bollinger Bands signal for the given symbol."""
        if not bars or len(bars) < self.period:
            return {
                "signal": "HOLD",
                "reason": "insufficient_data",
                "close": 0.0,
                "upper": 0.0,
                "lower": 0.0,
            }

        closes = [b.get("c") for b in bars if "c" in b]
        if len(closes) < self.period:
            return {
                "signal": "HOLD",
                "reason": "missing_close",
                "close": 0.0,
                "upper": 0.0,
                "lower": 0.0,
            }

        if any(c is None or (isinstance(c, float) and math.isnan(c)) for c in closes):
            return {
                "signal": "HOLD",
                "reason": "nan_detected",
                "close": 0.0,
                "upper": 0.0,
                "lower": 0.0,
            }

        try:
            sma = statistics.mean(closes[-self.period :])
            stdev = statistics.pstdev(closes[-self.period :])
        except Exception:
            return {
                "signal": "HOLD",
                "reason": "parse_error",
                "close": 0.0,
                "upper": 0.0,
                "lower": 0.0,
            }

        upper = sma + self.std_dev * stdev
        lower = sma - self.std_dev * stdev
        close = closes[-1]

        if stdev == 0:
            return {
                "signal": "HOLD",
                "reason": "flat_stdev",
                "close": close,
                "upper": upper,
                "lower": lower,
            }

        if close < lower:
            return {
                "signal": "BUY",
                "reason": "below_lower_band",
                "close": close,
                "upper": upper,
                "lower": lower,
            }
        if close > upper:
            return {
                "signal": "SELL",
                "reason": "above_upper_band",
                "close": close,
                "upper": upper,
                "lower": lower,
            }

        return {
            "signal": "HOLD",
            "reason": "within_bands",
            "close": close,
            "upper": upper,
            "lower": lower,
        }


def bollinger_bands_signal(
    bars: list[dict[str, Any]],
    period: int = 20,
    std_dev: float = 2.0,
    audit: bool = False,
) -> Union[str, tuple[str, float, float, float]]:
    """Module-level wrapper for Bollinger Bands signal."""
    signal = BollingerBandsSignal(period=period, std_dev=std_dev).generate(
        "SYMBOL", bars
    )

    decision = signal.get("signal", "HOLD")
    close = float(signal.get("close", 0.0))
    upper = float(signal.get("upper", 0.0))
    lower = float(signal.get("lower", 0.0))

    if audit:
        return decision, close, upper, lower
    return decision


__all__ = ["BollingerBandsSignal", "bollinger_bands_signal"]
