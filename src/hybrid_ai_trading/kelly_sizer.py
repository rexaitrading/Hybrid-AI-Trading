from __future__ import annotations

"""
Compatibility shim.
Phase-7 sweep expects: hybrid_ai_trading.kelly_sizer
Canonical implementation lives at: hybrid_ai_trading.risk.kelly_sizer
"""

from hybrid_ai_trading.risk.kelly_sizer import KellySizer

__all__ = ["KellySizer"]