# === vwap_model.py ===
import math
from dataclasses import dataclass

@dataclass
class VWAPResult:
    vwap: float
    distance: float
    slope: float
    regime: str
    confidence: float


class VWAPModel:
    def __init__(self):
        self.sum_px_vol = 0.0
        self.sum_vol = 0.0
        self.last_vwap = None

    def update(self, price, volume):
        self.sum_px_vol += price * volume
        self.sum_vol += volume

        if self.sum_vol == 0:
            return None

        vwap = self.sum_px_vol / self.sum_vol
        slope = 0 if self.last_vwap is None else vwap - self.last_vwap
        self.last_vwap = vwap
        distance = price - vwap

        if slope > 0 and price > vwap:
            regime = "trend_up"; conf = 0.7
        elif slope < 0 and price < vwap:
            regime = "trend_down"; conf = 0.7
        elif abs(distance) < 0.1 * vwap:
            regime = "neutral"; conf = 0.3
        else:
            regime = "revert"; conf = 0.5

        return VWAPResult(vwap, distance, slope, regime, conf)