from __future__ import annotations

"""
Phase-5 EV bands config loader.

This module provides a tiny, dependency-light interface for reading
config/phase5_ev_bands.yml and exposing EV band configuration to
the rest of the system.

Design goals:
- Safe if PyYAML is NOT installed (fallback parser).
- Works when the current working directory is the repo root
  (config/phase5_ev_bands.yml relative to CWD).
- Pure read-only: no writing / auto-creation here.
"""

from pathlib import Path
from typing import Any, Dict, Mapping, Optional


_CONFIG_REL_PATH = Path("config") / "phase5_ev_bands.yml"


def _parse_simple_ev_yaml(text: str) -> Dict[str, Dict[str, Any]]:
    """
    Very small YAML subset parser for files like:

        nvda_bplus_live:
          ev_band_abs: 0.50

        spy_orb_live:
          ev_band_abs: 0.50

    It ignores comments and blank lines. It does NOT try to be a full YAML
    implementation; it is only meant as a fallback if PyYAML is unavailable.
    """
    data: Dict[str, Dict[str, Any]] = {}
    current_section: Optional[str] = None

    for raw in text.splitlines():
        # Strip comments
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue

        if not line.startswith(" "):  # section header: "name:"
            header = line.strip()
            if not header.endswith(":"):
                # Not a section we understand; skip
                continue
            current_section = header[:-1].strip()
            if current_section not in data:
                data[current_section] = {}
            continue

        # Indented property line
        if current_section is None:
            continue

        stripped = line.strip()
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()

        # Try to coerce to float where possible
        if value == "":
            parsed: Any = None
        else:
            try:
                parsed = float(value)
            except ValueError:
                parsed = value

        data.setdefault(current_section, {})[key] = parsed

    return data


def _load_yaml_with_optional_pyyaml(path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Try to load YAML with PyYAML if available; otherwise fall back to the
    tiny built-in parser above.
    """
    text = path.read_text(encoding="utf-8")

    try:
        import yaml  # type: ignore[import]
    except Exception:
        # Fallback: no external dependency
        return _parse_simple_ev_yaml(text)

    loaded = yaml.safe_load(text)  # type: ignore[attr-defined]
    if loaded is None:
        return {}

    if not isinstance(loaded, Mapping):
        # Unexpected structure; do not crash, just return empty.
        return {}

    out: Dict[str, Dict[str, Any]] = {}
    for key, value in loaded.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, Mapping):
            out[key] = dict(value)
        else:
            # If the value is a scalar, wrap it in a dict
            out[key] = {"value": value}
    return out


def load_phase5_ev_bands(path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """
    Load the Phase-5 EV bands configuration.

    Parameters
    ----------
    path : Optional[Path]
        Optional override path. If not provided, we assume the current
        working directory is the repo root and look for:

            config/phase5_ev_bands.yml

    Returns
    -------
    Dict[str, Dict[str, Any]]
        Mapping of regime key -> dict of config fields, e.g.:

            {
              "nvda_bplus_live": {"ev_band_abs": 0.5},
              "spy_orb_live":    {"ev_band_abs": 0.5},
              "qqq_orb_live":    {"ev_band_abs": 0.5},
            }
    """
    cfg_path = path or _CONFIG_REL_PATH

    if not cfg_path.exists():
        # Graceful fallback: empty dict
        return {}

    return _load_yaml_with_optional_pyyaml(cfg_path)


def get_ev_band_abs(
    regime: str,
    config: Optional[Dict[str, Dict[str, Any]]] = None,
    default: Optional[float] = None,
) -> Optional[float]:
    """
    Convenience helper to get ev_band_abs for a given regime.

    Examples
    --------
    >>> cfg = load_phase5_ev_bands()
    >>> get_ev_band_abs("NVDA_BPLUS_LIVE", cfg)
    0.5
    """
    cfg = config if config is not None else load_phase5_ev_bands()
    if not cfg:
        return default

    regime_key = (regime or "").strip().lower()
    section = cfg.get(regime_key)
    if not section:
        # Try a slightly more relaxed key: strip suffixes like "_LIVE"
        if regime_key.endswith("_live"):
            base = regime_key[:-5]
            section = cfg.get(base)
        elif regime_key.endswith("_replay"):
            base = regime_key[:-7]
            section = cfg.get(base)

    if not section:
        return default

    val = section.get("ev_band_abs")
    if val is None:
        return default

    try:
        return float(val)
    except (TypeError, ValueError):
        return default