# src/hybrid_ai_trading/config/settings.py
"""
Settings Loader (Hybrid AI Quant Pro – Suite-Aligned, Hedge Fund Grade)
-----------------------------------------------------------------------
Central utility for loading and accessing the YAML configuration file.
"""

import os
import logging
from typing import Any, Dict

import yaml

logger = logging.getLogger("hybrid_ai_trading.config.settings")

# Project root and config path are constants for clarity and testability
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
)
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "config.yaml")


def _find_config_path() -> str:
    """Return absolute path to config/config.yaml."""
    return CONFIG_PATH


def load_config(force: bool = False) -> Dict[str, Any]:
    """
    Safely load config/config.yaml.
    If force=True, update the global CONFIG in this module.
    """
    config_path = _find_config_path()
    logger.debug("Looking for config at: %s", config_path)

    if not os.path.exists(config_path):
        logger.warning("Config file not found at: %s", config_path)
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
            if not isinstance(cfg, dict):
                logger.warning("Config file did not return a dict, forcing empty dict")
                cfg = {}
    except yaml.YAMLError as e:
        logger.error("Failed to parse YAML in config.yaml: %s", e)
        cfg = {}
    except Exception as e:  # noqa: BLE001
        logger.error("Unexpected error reading config.yaml: %s", e)
        cfg = {}

    if force:
        global CONFIG  # noqa: PLW0603
        CONFIG = cfg

    return cfg


def get_config_value(*keys: str, default: Any = None) -> Any:
    """Retrieve a nested config value with a safe default."""
    node: Any = CONFIG
    for key in keys:
        if isinstance(node, dict) and key in node:
            node = node[key]
        else:
            return default
    return node


# ---------------------------------------------------------------------
# Global CONFIG available at import time
# ---------------------------------------------------------------------
CONFIG: Dict[str, Any] = load_config()

__all__ = [
    "CONFIG",
    "load_config",
    "get_config_value",
    "_find_config_path",
    "PROJECT_ROOT",
    "CONFIG_PATH",
]
