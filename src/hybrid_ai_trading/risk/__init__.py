"""
Risk Package (Hybrid AI Quant Pro ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“ Hedge Fund Grade, Polished)
---------------------------------------------------------------
Centralized exports for risk governance modules.

Responsibilities:
- Provide unified imports for all risk management components.
- Avoid circular imports by only exposing stable, finalized classes.
- Ensure hedge-fund-grade quality across all risk layers.
"""

from .risk_manager import RiskManager
from .kelly_sizer import KellySizer
from .black_swan_guard import BlackSwanGuard
from .sentiment_filter import SentimentFilter
from .regime_detector import RegimeDetector

__all__ = [
    "RiskManager",
    "KellySizer",
    "BlackSwanGuard",
    "SentimentFilter",
    "RegimeDetector",
]

from . import patch_kwargs  # ensure RiskManager ctor accepts legacy kwargs

from . import patch_api  # compat: add missing RiskManager API

from . import patch_exposure  # compat: portfolio exposure guard
