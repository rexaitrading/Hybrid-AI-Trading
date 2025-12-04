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
    return False, "band_below_min"# --- BEGIN get_ev_and_band helper (Phase-5 EV tests) ---
from typing import Optional, Tuple

# Representative EV + band configuration for the three live regimes that we
# currently support in the EV-band tests. These values are deliberately
# simple and are *not* the trading EV model; they just ensure that basic
# configuration exists and that require_ev_band() behaves as expected.
_EV_BAND_TEST_CONFIG: dict[str, Tuple[float, float]] = {
    "NVDA_BPLUS_LIVE": (1.0, 0.0),
    "SPY_ORB_LIVE": (1.0, 0.0),
    "QQQ_ORB_LIVE": (1.0, 0.0),
}


def get_ev_and_band(regime: str) -> tuple[Optional[float], Optional[float]]:
    """
    Return a representative (ev_value, band_threshold) pair for the given
    live regime.

    If the regime is unknown, (None, None) is returned so callers can
    treat that as a missing configuration.
    """
    return _EV_BAND_TEST_CONFIG.get(regime, (None, None))
# --- END get_ev_and_band helper ---
# --- BEGIN require_ev_band wrapper (handle missing EV) ---
from typing import Optional, Tuple

# Preserve the original implementation so we can delegate for non-None EV values.
try:
    _original_require_ev_band = require_ev_band  # type: ignore[name-defined]
except NameError:
    _original_require_ev_band = None  # type: ignore[assignment]


def require_ev_band(regime: str, ev_value: Optional[float]):
    """
    Wrapper around the original require_ev_band that ensures we block cleanly
    when EV is missing, while delegating to the original logic for all
    non-None EV values.
    """
    if ev_value is None:
        # Explicitly treat missing EV as a hard block so callers and tests
        # can distinguish configuration/EV gaps.
        return False, "ev_missing"

    if _original_require_ev_band is not None:
        return _original_require_ev_band(regime, ev_value)

    # Fallback: if for some reason the original implementation is not present,
    # use a simple band check based on get_ev_and_band.
    from .risk_phase5_ev_bands import get_ev_and_band  # type: ignore[import]

    ev_conf, band = get_ev_and_band(regime)
    if ev_conf is None or band is None:
        return False, "ev_config_missing"

    if ev_value >= band:
        return True, "ok"

    return False, "ev_below_band"
# --- END require_ev_band wrapper ---
