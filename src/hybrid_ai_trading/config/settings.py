# src/config/settings.py
"""
Settings Loader (Hybrid AI Quant Pro v9.0 – AAA Polished & 100% Coverage)
-------------------------------------------------------------------------
Central utility for loading and accessing the YAML configuration file.

Features:
- Loads `config/config.yaml` relative to project root
- Supports dynamic upgrades:
  * regime.min_samples: "auto" → int(lookback_days * 0.7), min=2
  * Kelly sizing safeguard: disables if win_rate<=0 or payoff<=0
- Returns {} safely if file missing or invalid
- Provides `get_config_value()` helper for nested keys with safe defaults
- Singleton CONFIG object for project-wide access
- Works in local dev, CI/CD, and production environments
"""

import yaml
from pathlib import Path
from typing import Any, Dict

# === Locate project root & config.yaml ===
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"


def _apply_upgrades(cfg: Dict) -> Dict:
    """
    Apply Hybrid AI Quant Pro dynamic upgrades to the raw config.
    """
    if not isinstance(cfg, dict):
        return {}

    # --- Regime Detection Upgrades ---
    regime_cfg = cfg.get("regime")
    if isinstance(regime_cfg, dict):
        lookback = regime_cfg.get("lookback_days", 90)
        if str(regime_cfg.get("min_samples", "")).lower() == "auto":
            regime_cfg["min_samples"] = max(2, int(lookback * 0.7))  # safeguard min=2
        cfg["regime"] = regime_cfg

    # --- Kelly sizing safeguard ---
    risk_cfg = cfg.get("risk")
    if isinstance(risk_cfg, dict):
        kelly_cfg = risk_cfg.get("kelly", {})
        if kelly_cfg.get("enabled", False):
            win_rate = float(kelly_cfg.get("win_rate", 0.5))
            payoff = float(kelly_cfg.get("payoff", 1.0))
            if win_rate <= 0 or payoff <= 0:
                print("⚠️ Kelly config invalid → disabling Kelly sizing")
                kelly_cfg["enabled"] = False
        cfg["risk"]["kelly"] = kelly_cfg

    return cfg


def load_config(path: Path = CONFIG_PATH) -> Dict:
    """
    Load the main config/config.yaml file safely.

    Returns
    -------
    dict
        Parsed YAML config as a dictionary, post-upgrades, or {} if not found/invalid.
    """
    print(f"🔍 Looking for config at: {path}")

    if not path.exists():
        print(f"⚠️ Config file not found at: {path}")
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_cfg = yaml.safe_load(f) or {}
            return _apply_upgrades(raw_cfg)
    except yaml.YAMLError as e:
        print(f"❌ Failed to parse config.yaml: {e}")
        return {}
    except Exception as e:
        print(f"❌ Unexpected error loading config.yaml: {e}")
        return {}


def get_config_value(*keys: str, default: Any = None) -> Any:
    """
    Retrieve a nested config value with a safe default.

    Parameters
    ----------
    *keys : str
        Sequence of keys to traverse in the config.
    default : any, optional
        Value to return if the key is not found.

    Returns
    -------
    any
        Value from config, or default if missing.
    """
    node: Any = CONFIG
    for key in keys:
        if isinstance(node, dict) and key in node:
            node = node[key]
        else:
            return default
    return node


# === Singleton config object (used everywhere) ===
CONFIG: Dict = load_config()

__all__ = [
    "CONFIG",
    "load_config",
    "get_config_value",
    "_apply_upgrades",
    "CONFIG_PATH",
    "PROJECT_ROOT",
]
