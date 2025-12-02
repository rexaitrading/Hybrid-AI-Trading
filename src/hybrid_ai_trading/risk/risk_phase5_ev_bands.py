from __future__ import annotations

"""
Simple Phase-5 EV-band rules.

Central function:

    require_ev_band(regime: str, ev: float) -> tuple[bool, str]

Returns:
    allowed: bool
    reason: str  (e.g. "ev_missing", "ev_not_numeric", "band_A", "band_B", "band_below_min")

This module is currently used in a *log-only* fashion via ev_band_flags.evaluate_ev_band_for_trade(),
so it does not perform any hard veto by itself. It just classifies EV into bands.
"""

from typing import Dict, Tuple

# Per-regime absolute EV thresholds.
# You can tune these as you refine your ORB/VWAP strategies.
_EV_BAND_CONFIG: Dict[str, Dict[str, float]] = {
    # NVDA B+ live regime
    "NVDA_BPLUS_LIVE": {
        "A": 0.02,   # strong EV
        "B": 0.01,   # moderate EV
    },
    # SPY ORB live
    "SPY_ORB_LIVE": {
        "A": 0.015,
        "B": 0.008,
    },
    # QQQ ORB live
    "QQQ_ORB_LIVE": {
        "A": 0.015,
        "B": 0.008,
    },
}

# Default thresholds if regime not explicitly listed
_DEFAULT_BANDS = {"A": 0.02, "B": 0.01}


def _get_band_thresholds(regime: str) -> Dict[str, float]:
    return _EV_BAND_CONFIG.get(regime, _DEFAULT_BANDS)


def require_ev_band(regime: str, ev: float) -> Tuple[bool, str]:
    """
    Classify EV into bands for a given regime.

    Args:
        regime: strategy regime name (e.g. "NVDA_BPLUS_LIVE")
        ev: expected value for this trade

    Returns:
        allowed, reason

    Reasons:
        - "ev_missing"       : ev is None
        - "ev_not_numeric"   : ev could not be converted to float
        - "band_A"           : |ev| >= A_threshold
        - "band_B"           : |ev| >= B_threshold but < A_threshold
        - "band_below_min"   : |ev| < B_threshold
    """
    if ev is None:
        return True, "ev_missing"

    try:
        ev_abs = abs(float(ev))
    except (TypeError, ValueError):
        return True, "ev_not_numeric"

    bands = _get_band_thresholds(regime)
    a_thr = float(bands.get("A", _DEFAULT_BANDS["A"]))
    b_thr = float(bands.get("B", _DEFAULT_BANDS["B"]))

    if ev_abs >= a_thr:
        return True, "band_A"
    if ev_abs >= b_thr:
        return True, "band_B"
    return False, "band_below_min"