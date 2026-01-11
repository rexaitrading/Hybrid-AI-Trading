from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Signal:
    action: str  # "HOLD" | "BUY" | "SELL"
    confidence: float
    reason: str


class SimpleStrategy:
    """
    Deterministic toy strategy for simulation ONLY.
    Uses last N prices; buy if last > mean*(1+thr), sell if last < mean*(1-thr).
    """

    def __init__(self, lookback: int = 20, thr: float = 0.002):
        self.lookback = int(max(5, lookback))
        self.thr = float(max(0.0, thr))
        self.hist: Dict[str, List[float]] = {}

    def on_price(self, symbol: str, px: float) -> Signal:
        h = self.hist.setdefault(symbol, [])
        h.append(float(px))
        if len(h) > self.lookback:
            del h[: len(h) - self.lookback]

        if len(h) < self.lookback:
            return Signal("HOLD", 0.0, f"warmup({len(h)}/{self.lookback})")

        mean = sum(h) / len(h)
        last = h[-1]
        up = mean * (1.0 + self.thr)
        dn = mean * (1.0 - self.thr)

        if last > up:
            return Signal("BUY", 0.2, "last>mean+thr (toy)")
        if last < dn:
            return Signal("SELL", 0.2, "last<mean-thr (toy)")
        return Signal("HOLD", 0.0, "inside_band")

    def on_price_with_hist(self, symbol: str, px: float, hist: Dict[str, List[float]]) -> Signal:
        h = hist.setdefault(symbol, [])
        h.append(float(px))
        if len(h) > self.lookback:
            del h[: len(h) - self.lookback]

        if len(h) < self.lookback:
            return Signal("HOLD", 0.0, f"warmup({len(h)}/{self.lookback})")

        mean = sum(h) / len(h)
        last = h[-1]
        up = mean * (1.0 + self.thr)
        dn = mean * (1.0 - self.thr)

        if last > up:
            return Signal("BUY", 0.2, "last>mean+thr (toy)")
        if last < dn:
            return Signal("SELL", 0.2, "last<mean-thr (toy)")
        return Signal("HOLD", 0.0, "inside_band")

