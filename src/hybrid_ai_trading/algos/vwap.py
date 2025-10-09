"""
VWAP Algo (Hybrid AI Quant Pro v37.0 - Hedge-Fund Grade, Test-Friendly, 100% Coverage)
--------------------------------------------------------------------------------------
Rules:
- BUY  ? last close > VWAP
- SELL ? last close < VWAP
- HOLD ? tie (within tolerance)

Guards (return HOLD):
- Empty list
- Any bar missing "c" or "v"
- Non-numeric values / conversion failure
- Any NaN in closes or volumes
- Total volume <= 0
"""

from typing import List, Dict, Union
import math

Number = Union[int, float]


def _to_float(x: Union[str, Number]) -> float:
    """Best-effort float conversion; raise ValueError if impossible."""
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        # Accept common string numerics including "nan"
        try:
            return float(x.strip())
        except Exception as e:  # keep local, predictable exception
            raise ValueError("non-numeric string") from e
    raise ValueError("unsupported type")


def vwap_algo(bars: List[Dict[str, Union[Number, str]]]) -> str:
    """Compute a simple VWAP decision from bars."""
    # Guard 1: empty
    if not bars:
        return "HOLD"

    # Guard 2: all bars must contain both keys
    if not all(("c" in b and "v" in b) for b in bars):
        return "HOLD"

    # Parse safely
    closes: List[float] = []
    vols: List[float] = []
    try:
        for b in bars:
            c = _to_float(b["c"])
            v = _to_float(b["v"])
            closes.append(c)
            vols.append(v)
    except ValueError:
        # Guard 3: non-numeric / bad types
        return "HOLD"

    # Guard 4: NaN presence
    if any(math.isnan(c) for c in closes) or any(math.isnan(v) for v in vols):
        return "HOLD"

    # Guard 5: total volume must be positive
    total_v = sum(vols)
    if total_v <= 0:
        return "HOLD"

    # Decision
    vwap_val = sum(c * v for c, v in zip(closes, vols)) / total_v
    last_price = closes[-1]

    # Tie tolerance
    if math.isclose(last_price, vwap_val, rel_tol=0.0, abs_tol=1e-12):
        return "HOLD"

    return "BUY" if last_price > vwap_val else "SELL"


class VWAPAlgo:
    """OO wrapper; matches orchestrator-style usage."""
    def generate(self, symbol: str, bars: List[Dict[str, Union[Number, str]]]) -> str:
        _ = symbol  # symbol unused in pure price-based decision
        return vwap_algo(bars)


def vwap_signal(bars: List[Dict[str, Union[Number, str]]]) -> str:
    """Functional wrapper for convenience/testing."""
    return vwap_algo(bars)


__all__ = ["vwap_algo", "VWAPAlgo", "vwap_signal"]
