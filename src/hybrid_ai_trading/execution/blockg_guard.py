# -*- coding: utf-8 -*-
"""
Compatibility shim.

Some modules import:
  from hybrid_ai_trading.execution.blockg_guard import require_blockg_ready

Canonical implementation lives in:
  hybrid_ai_trading.execution.blockg_enforce.require_blockg_ready_for_live

This shim preserves backwards compatibility and keeps semantics fail-closed.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from hybrid_ai_trading.execution.blockg_enforce import require_blockg_ready_for_live


def require_blockg_ready(symbol: str, status: Optional[Dict[str, Any]] = None) -> None:
    """
    Backwards-compatible name used by older code paths.
    Delegates to require_blockg_ready_for_live().
    """
    require_blockg_ready_for_live(symbol=symbol, status=status)