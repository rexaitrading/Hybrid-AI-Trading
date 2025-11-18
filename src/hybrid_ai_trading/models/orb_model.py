# === orb_model.py ===
import math
from dataclasses import dataclass

@dataclass
class ORBResult:
    orb_high: float
    orb_low: float
    breakout: str
    confidence: float
    reason: str


class ORBModel:
    """
    Opening Range Breakout (ORB) model.
    Computes ORB high/low for first N minutes and detects breaks.
    """
    def __init__(self, orb_minutes=5):
        self.orb_minutes = orb_minutes
        self.reset()

    def reset(self):
        self.orb_high = None
        self.orb_low = None
        self.ready = False

    def update_bar(self, ts, high, low):
        if not self.ready:
            if self.orb_high is None:
                self.orb_high = high
                self.orb_low = low
            else:
                self.orb_high = max(self.orb_high, high)
                self.orb_low = min(self.orb_low, low)

    def finalize(self):
        self.ready = True

    def evaluate(self, price):
        if not self.ready:
            return ORBResult(None, None, "none", 0.0, "ORB not ready")

        if price > self.orb_high:
            return ORBResult(self.orb_high, self.orb_low, "up", 0.7, "breakout_up")

        if price < self.orb_low:
            return ORBResult(self.orb_high, self.orb_low, "down", 0.7, "breakout_down")

        return ORBResult(self.orb_high, self.orb_low, "none", 0.1, "inside_range")