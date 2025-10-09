"""
Pipelines package initializer (Hybrid AI Quant Pro – Polished).
---------------------------------------------------------------
Exposes pipeline modules for clean imports, with safe guards.
"""

import logging

logger = logging.getLogger(__name__)

# Try safe import of daily_close, but don't block package if it fails
try:
    from . import daily_close
except Exception as e:  # noqa: BLE001
    daily_close = None  # fallback
    logger.warning("⚠️ Failed to import daily_close pipeline: %s", e)

__all__ = ["daily_close"]
