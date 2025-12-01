"""
Helpers to load Phase-5 JSON configs for SPY ORB (and others later).

Currently used by:
- tools/mock_phase5_spy_orb_runner.py

Config JSON is expected at:
- config/phase5/spy_orb_phase5.json
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

# Central EV bands loader (YAML-based):
# config/phase5_ev_bands.yml -> load_phase5_ev_bands / get_ev_band_abs
try:
    from config.phase5_config_loader import load_phase5_ev_bands, get_ev_band_abs
except Exception:  # pragma: no cover - defensive fallback
    load_phase5_ev_bands = None  # type: ignore[assignment]
    get_ev_band_abs = None       # type: ignore[assignment]


def load_spy_orb_phase5_config(path: str = "config/phase5/spy_orb_phase5.json") -> Dict[str, Any]:
    """
    Load the raw SPY ORB Phase-5 JSON config.

    This is the legacy / baseline loader that existing callers use.
    """
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"SPY ORB Phase-5 config not found at {cfg_path}")

    with cfg_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"SPY ORB config at {cfg_path} must be a JSON object (dict)")

    return data


def load_spy_orb_phase5_config_with_ev(
    path: str = "config/phase5/spy_orb_phase5.json",
    ev_bands_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Load SPY ORB Phase-5 config and, if available, enrich it with EV band
    information from config/phase5_ev_bands.yml.

    The YAML is read via config.phase5_config_loader, and we look up the
    EV band for regime key "SPY_ORB_LIVE" (case-insensitive). If found,
    we attach it into the JSON config under a couple of conventional keys:

        cfg["ev"]["ev_band_abs"]
        cfg["phase5"]["ev_band_abs"]

    so callers can choose whichever nesting is more convenient.

    If the YAML loader is not available, or no band is configured, the
    JSON config is returned unchanged.
    """
    cfg = load_spy_orb_phase5_config(path)

    # If central EV loader is unavailable, just return the raw config.
    if load_phase5_ev_bands is None or get_ev_band_abs is None:
        return cfg

    try:
        ev_cfg = load_phase5_ev_bands(ev_bands_path)
        band = get_ev_band_abs("SPY_ORB_LIVE", ev_cfg, default=None)
    except Exception:
        # Do not crash config loading if EV bands are misconfigured; just
        # return the baseline JSON config.
        return cfg

    if band is None:
        return cfg

    # Attach into a couple of conventional locations.
    ev_section = cfg.setdefault("ev", {})
    if isinstance(ev_section, dict):
        ev_section["ev_band_abs"] = band

    phase5_section = cfg.setdefault("phase5", {})
    if isinstance(phase5_section, dict):
        phase5_section["ev_band_abs"] = band

    return cfg