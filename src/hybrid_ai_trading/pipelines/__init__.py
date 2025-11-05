"""
Pipelines package initializer (Hybrid AI Quant Pro Ã¢â‚¬â€œ Polished).
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
    logger.warning("Ã¢Å¡Â Ã¯Â¸Â Failed to import daily_close pipeline: %s", e)

__all__ = ["daily_close"]


def note_fill_failure_phrase():
    logger.error("fill simulation failed")
