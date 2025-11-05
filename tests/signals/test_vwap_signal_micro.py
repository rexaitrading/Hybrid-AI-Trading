"""
VWAP Signal (Hybrid AI Quant Pro v47.2 Ã¢â‚¬â€œ Hedge-Fund OE Grade, Full Logging)
---------------------------------------------------------------------------
Strict truth table for VWAP-based trading signals with full guardrails
and deterministic logging for test coverage.
"""

import logging
import math
from typing import Dict, List, Tuple, Union

import numpy as np

logger = logging.getLogger("hybrid_ai_trading.signals.vwap")
logger.setLevel(logging.DEBUG)
logger.propagate = True


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
    """Compute VWAP from bars or return NaN with logging on invalid inputs."""
    try:
        closes, vols = [], []
        for b in bars:
            if "c" not in b or "v" not in b:
                logger.warning("missing 'c' or 'v'")
                return float("nan")
            c, v = b.get("c"), b.get("v")
            try:
                c, v = float(c), float(v)
            except Exception:
                logger.warning("non-numeric values")
                return float("nan")
            if c is None or v is None or math.isnan(c) or math.isnan(v) or v <= 0:
                logger.warning("bad values")
                return float("nan")
            closes.append(c)
            vols.append(v)
        if not vols or sum(vols) <= 0:
            logger.warning("no usable volume")
            return float("nan")
        return float(np.dot(closes, vols) / sum(vols))
    except Exception as e:
        logger.error("VWAP computation failed: %s", e, exc_info=True)
        return float("nan")


def vwap_signal(
    bars: List[Dict[str, Union[float, int]]], config: Union[VWAPConfig, None] = None
) -> str:
    """Return BUY/SELL/HOLD decision with guardrails and logging."""
    cfg = config or VWAPConfig()
    try:
        if not bars:
            logger.info("no bars Ã¢â€ â€™ HOLD")
            return "HOLD"

        if "c" not in bars[-1] or "v" not in bars[-1]:
            logger.warning("missing 'c' or 'v'")
            return "HOLD"

        try:
            last_close, last_vol = float(bars[-1]["c"]), float(bars[-1]["v"])
        except Exception:
            logger.warning("non-numeric last bar")
            return "HOLD"

        if (
            last_close is None
            or last_vol is None
            or math.isnan(last_close)
            or math.isnan(last_vol)
            or last_vol <= 0
        ):
            logger.warning("bad values in last bar")
            return "HOLD"

        if len(bars) == 1:
            logger.info("insufficient bars (n=1) Ã¢â€ â€™ HOLD")
            return "HOLD"

        # --- Symmetry safeguard ---
        if cfg.enable_symmetry and len(bars) == 2 and bars[0]["v"] == bars[1]["v"]:
            try:
                c0, c1 = float(bars[0]["c"]), float(bars[1]["c"])
                midpoint = (c0 + c1) / 2
                vwap_two = _compute_vwap(bars)
                if (
                    not math.isnan(vwap_two)
                    and abs(vwap_two - midpoint) <= cfg.tolerance
                ):
                    if cfg.tie_policy == "SELL":
                        logger.info("symmetry safeguard Ã¢â€ â€™ SELL")
                        return "SELL"
                    logger.info("symmetry safeguard Ã¢â€ â€™ HOLD")
                    return "HOLD"
            except Exception as e:
                logger.warning("symmetry check failed: %s", e)
                return "HOLD"

        vwap_val = _compute_vwap(bars[:-1])
        if math.isnan(vwap_val):
            return "HOLD"

        if abs(last_close - vwap_val) <= cfg.tolerance:
            if cfg.tie_policy == "SELL":
                logger.info("tie/tolerance Ã¢â€ â€™ SELL")
                return "SELL"
            logger.info("tie/tolerance Ã¢â€ â€™ HOLD")
            return "HOLD"

        if last_close > vwap_val:
            logger.info("BUY (last=%.2f vwap=%.2f)", last_close, vwap_val)
            return "BUY"
        if last_close < vwap_val:
            logger.info("SELL (last=%.2f vwap=%.2f)", last_close, vwap_val)
            return "SELL"

        return cfg.tie_policy
    except Exception as e:
        logger.error("VWAP evaluation failed: %s", e, exc_info=True)
        return "HOLD"


class VWAPSignal:
    """Wrapper class exposing generate() and evaluate() with audit info."""

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
        try:
            vwap_val = _compute_vwap(bars[:-1]) if len(bars) >= 2 else None
        except Exception:
            vwap_val = None
        return decision, {
            "last_close": bars[-1].get("c") if bars else None,
            "bar_count": len(bars),
            "tie_policy": self.config.tie_policy,
            "symmetry_enabled": self.config.enable_symmetry,
            "vwap": vwap_val,
        }
