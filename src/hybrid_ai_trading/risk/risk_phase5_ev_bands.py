from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# Config locations
# ---------------------------------------------------------------------------

EV_JSON = Path("config") / "phase5" / "ev_simple.json"
BANDS_YAML = Path("config") / "phase5_ev_bands.yml"

# Cached copies so we do not hit disk on every trade
_EV_CACHE: Optional[Dict[str, float]] = None
_BANDS_CACHE: Optional[Dict[str, float]] = None


# ---------------------------------------------------------------------------
# Internal loaders (shared with analyzers / gating)
# ---------------------------------------------------------------------------

def _load_ev_simple() -> Dict[str, float]:
    """
    Load per-trade EV configuration from EV_JSON.

    Returns a mapping of regime name (e.g. "NVDA_BPLUS_LIVE") to EV per trade.
    Missing file or malformed entries are treated as "no config".
    """
    out: Dict[str, float] = {}

    if not EV_JSON.exists():
        return out

    with EV_JSON.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # NVDA stored as a scalar in your current layout
    nvda_val = data.get("NVDA_BPLUS_LIVE")
    if nvda_val is not None:
        try:
            out["NVDA_BPLUS_LIVE"] = float(nvda_val)
        except (TypeError, ValueError):
            # ignore malformed entries
            pass

    # SPY / QQQ stored as dicts with "ev_per_trade"
    for key in ("SPY_ORB_LIVE", "QQQ_ORB_LIVE"):
        cfg = data.get(key)
        if isinstance(cfg, dict):
            val = cfg.get("ev_per_trade")
            if val is not None:
                try:
                    out[key] = float(val)
                except (TypeError, ValueError):
                    # ignore malformed entries
                    pass

    return out


def _load_bands_yaml() -> Dict[str, float]:
    """
    Very small YAML reader specialized for phase5_ev_bands.yml format:

        regime_lowercase:
          ev_band_abs: 0.0123

    We keep this parser minimal so that we don't need pyyaml.
    """
    if not BANDS_YAML.exists():
        return {}

    text = BANDS_YAML.read_text(encoding="utf-8")
    lines = [ln.rstrip("\n") for ln in text.splitlines()]

    bands: Dict[str, float] = {}
    current_key: Optional[str] = None

    for ln in lines:
        line = ln.strip()
        if not line or line.startswith("#"):
            continue

        # regime key line: nvda_bplus_live:
        if line.endswith(":") and not line.startswith("ev_band_abs"):
            current_key = line.rstrip(":").strip()
            continue

        # value line: ev_band_abs: 0.0123
        if line.startswith("ev_band_abs:") and current_key:
            _, val_str = line.split(":", 1)
            val_str = val_str.strip()
            try:
                bands[current_key] = float(val_str)
            except ValueError:
                # ignore malformed numbers
                pass

    return bands


# ---------------------------------------------------------------------------
# Public helpers: cached config views
# ---------------------------------------------------------------------------

def get_ev_config() -> Dict[str, float]:
    """
    Return cached EV configuration mapping regime -> EV per trade.

    Example keys:
      - "NVDA_BPLUS_LIVE"
      - "SPY_ORB_LIVE"
      - "QQQ_ORB_LIVE"
    """
    global _EV_CACHE
    if _EV_CACHE is None:
        _EV_CACHE = _load_ev_simple()
    return _EV_CACHE


def get_ev_bands() -> Dict[str, float]:
    """
    Return cached EV band configuration mapping regime_lowercase -> ev_band_abs.

    Example keys:
      - "nvda_bplus_live"
      - "spy_orb_live"
      - "qqq_orb_live"
    """
    global _BANDS_CACHE
    if _BANDS_CACHE is None:
        _BANDS_CACHE = _load_bands_yaml()
    return _BANDS_CACHE


def refresh_from_disk() -> None:
    """
    Clear caches so the next call reloads ev_simple.json and phase5_ev_bands.yml.

    This is useful when EV tuning or band files are updated on disk and you want
    the live process to pick up the new numbers without a restart.
    """
    global _EV_CACHE, _BANDS_CACHE
    _EV_CACHE = None
    _BANDS_CACHE = None


def get_ev_and_band(regime: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Convenience helper used by gating code.

    Returns (ev_per_trade, ev_band_abs) for the given regime.

    - ev_per_trade is looked up using the regime key as-is,
      e.g. "NVDA_BPLUS_LIVE".
    - ev_band_abs is looked up using regime.lower(),
      e.g. "nvda_bplus_live".
    """
    ev_cfg = get_ev_config().get(regime)
    band_abs = get_ev_bands().get(regime.lower())
    return ev_cfg, band_abs


# ---------------------------------------------------------------------------
# Core EV-band gating helper
# ---------------------------------------------------------------------------

def require_ev_band(regime: str, ev_for_trade: Optional[float]) -> Tuple[bool, str]:
    """
    Phase-5 EV band gating.

    Returns (allowed, reason):

    - (False, "ev_config_missing") if either EV or band config is missing.
    - (False, "ev_missing")        if ev_for_trade is None.
    - (False, "ev_below_band")     if |ev_for_trade| < ev_band_abs.
    - (True,  "ev_band_ok")        otherwise.

    NOTE:
      Today ev_for_trade will typically equal the configured EV per trade from
      ev_simple.json. This helper is designed so that later you can pass a more
      detailed EV (e.g. adjusted for costs, regime microstructure, etc.)
      without changing the RiskManager / runner call sites.
    """
    ev_cfg, band_abs = get_ev_and_band(regime)

    if ev_cfg is None or band_abs is None:
        return False, "ev_config_missing"

    if ev_for_trade is None:
        return False, "ev_missing"

    if abs(ev_for_trade) < band_abs:
        return False, "ev_below_band"

    return True, "ev_band_ok"