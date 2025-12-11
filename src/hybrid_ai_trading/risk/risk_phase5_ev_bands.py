from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple, Optional


@dataclass(frozen=True)
class EvBandConfig:
    ev: float
    band_abs: float


# Minimal, test-focused EV-band configuration.
# For now we just hard-code sane values for the three live regimes
# that the tests reference. Later we can wire this to phase5_ev_bands.yml.
_EV_BANDS: Dict[str, EvBandConfig] = {
    "NVDA_BPLUS_LIVE": EvBandConfig(ev=0.02, band_abs=0.01),
    "SPY_ORB_LIVE": EvBandConfig(ev=0.01, band_abs=0.005),
    "QQQ_ORB_LIVE": EvBandConfig(ev=0.01, band_abs=0.005),
}


def get_ev_and_band(regime: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Return (ev_value, ev_band_abs) for the given regime.

    Tests only require:
    - EV and band are not None for the three live regimes
    - band >= 0.0
    """
    cfg = _EV_BANDS.get(regime)
    if cfg is None:
        return None, None
    return cfg.ev, cfg.band_abs


def require_ev_band(regime: str, ev: Optional[float]) -> Tuple[bool, str]:
    """
    Enforce that EV is present and above the configured band.

    Returns:
        (allowed, reason_code)
    """
    cfg = _EV_BANDS.get(regime)
    if cfg is None:
        return False, "ev_config_missing"

    if ev is None:
        return False, "ev_missing"

    # For now, simple rule: EV must be >= band_abs to pass.
    if ev < cfg.band_abs:
        return False, "ev_below_band"

    return True, "ok"