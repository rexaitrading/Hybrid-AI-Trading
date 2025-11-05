"""
Hybrid AI Trading â€“ Config Package (Hedge Fund Grade)
-----------------------------------------------------
Holds configuration loaders and settings for the trading system.
"""

# Expose config loader utilities at the package level.
from .settings import load_config  # noqa: F401

__all__ = ["load_config"]
