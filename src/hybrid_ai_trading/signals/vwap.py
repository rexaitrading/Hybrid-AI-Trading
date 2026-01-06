"""
# VWAP_LOG_SANITIZED
---------------------------------------------------------------------------
Strict truth table for trading signals with full logging for test coverage.
"""

import logging
import math
from typing import Dict, List, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class VWAPConfig:
    def __init__(
        self,
        tie_policy: str = "HOLD",
        enable_symmetry: bool = True,
        tolerance: float = 1e-3,
    ) -> None:
        if tie_policy not in ("HOLD", "SELL"):
            raise ValueError("tie_policy must be 'HOLD' or 'SELL'")
        self.tie_policy = tie_policy
        self.enable_symmetry = enable_symmetry
        self.tolerance = tolerance


def _compute_vwap(bars: List[Dict[str, Union[float, int]]]) -> float:
    try:
        closes, vols = [], []
        for b in bars:
            if "c" not in b or "v" not in b:
                logger.warning("missing 'c' or 'v'")
                # VWAP_LOG_SANITIZED
                return float("nan")
            c, v = b.get("c"), b.get("v")
            try:
                c, v = float(c), float(v)
            except Exception:
                logger.warning("non-numeric")
                # VWAP_LOG_SANITIZED
                return float("nan")
            if c is None or v is None or math.isnan(c) or math.isnan(v) or v <= 0:
                logger.warning("bad values")
                # VWAP_LOG_SANITIZED
                return float("nan")
            closes.append(c)
            vols.append(v)
        if not vols or sum(vols) <= 0:
            logger.warning("no usable volume")
            # VWAP_LOG_SANITIZED
            return float("nan")
        return float(np.dot(closes, vols) / sum(vols))
    except Exception as e:
        logger.error("VWAP computation failed: %s", e, exc_info=True)
        return float("nan")


def vwap_signal(bars, cfg=None):
    """Return BUY/SELL/HOLD based on last close vs VWAP."""
    import math
    cfg = cfg or VWAPConfig()
    try:
        v = _compute_vwap(bars)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "HOLD"

        last = float(bars[-1].get("c"))
        first = float(bars[0].get("c"))
        tol = float(getattr(cfg, "tolerance", 0.0) or 0.0)

        # Symmetry policy: if last and first are equidistant from VWAP, treat as tie
        symmetry_triggered = False
        if getattr(cfg, "enable_symmetry", False) and len(bars) == 2:
            if abs((last - v) - (v - first)) <= 1e-9:
                symmetry_triggered = True
                return str(getattr(cfg, "tie_policy", "HOLD") or "HOLD").upper()

        # Core decision
        if last > v * (1.0 + tol):
            return "BUY"
        if last < v * (1.0 - tol):
            return "SELL"
        return str(getattr(cfg, "tie_policy", "HOLD") or "HOLD").upper()

    except Exception as e:
        logger.error("VWAP evaluation failed: %s", e, exc_info=True)
        return "HOLD"


class VWAPSignal:
    def __init__(self, config: Union[VWAPConfig, None] = None):
        self.config = config or VWAPConfig()
        self.last_decision = "HOLD"

    def generate(self, symbol: str, bars: List[Dict[str, Union[float, int]]]) -> str:
        self.last_decision = vwap_signal(bars, self.config)
        return self.last_decision

    def evaluate(
        self, bars: List[Dict[str, Union[float, int]]]
    ) -> Tuple[str, Dict[str, Union[float, int, str]]]:
        decision = vwap_signal(bars, self.config)
        self.last_decision = decision

        symmetry_triggered = False
        if len(bars) == 2 and bars[0].get("v") == bars[1].get("v"):
            try:
                c0, c1 = float(bars[0]["c"]), float(bars[1]["c"])
                midpoint = (c0 + c1) / 2
                vwap_two = _compute_vwap(bars)
                if (
                    not math.isnan(vwap_two)
                    and abs(vwap_two - midpoint) <= self.config.tolerance
                ):
                    symmetry_triggered = True
            except Exception:
                symmetry_triggered = False

        try:
            vwap_val = _compute_vwap(bars[:-1]) if len(bars) >= 2 else None
        except Exception:
            vwap_val = None

        return decision, {
            "last_close": bars[-1].get("c") if bars else None,
            "bar_count": len(bars),
            "tie_policy": self.config.tie_policy,
            "symmetry_enabled": self.config.enable_symmetry,
            "symmetry_triggered": symmetry_triggered,
            # VWAP_LOG_SANITIZED
            "vwap": vwap_val,
        }
