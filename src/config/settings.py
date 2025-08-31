# src/config/settings.py
"""
Settings Loader
---------------
Central utility for loading and accessing the YAML configuration file.

Features:
- Loads config/config.yaml relative to project root
- Returns {} safely if file missing or invalid
- Provides get_config_value() helper for nested keys
- Works in local dev, CI/CD, and production
"""

import os
import yaml


def load_config():
    """
    Load the main config/config.yaml file safely.

    Returns
    -------
    dict
        Parsed YAML config as a dictionary, or {} if not found/invalid.
    """
    # Locate project root (two levels up from this file: src/config/ -> project root)
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
    )
    config_path = os.path.join(project_root, "config", "config.yaml")

    # Debugging trace (shows up in CI logs)
    print(f"🔎 Looking for config at: {config_path}")

    if not os.path.exists(config_path):
        print(f"⚠️ Config file not found at: {config_path}")
        return {}

    try:
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
            if not isinstance(cfg, dict):
                print("⚠️ Config file did not return a dict, forcing empty dict")
                return {}
            return cfg
    except Exception as e:
        print(f"❌ Failed to load/parse config.yaml: {e}")
        return {}


def get_config_value(*keys, default=None):
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
    cfg = load_config()
    node = cfg
    for key in keys:
        if isinstance(node, dict) and key in node:
            node = node[key]
        else:
            return default
    return node


__all__ = ["load_config", "get_config_value"]
