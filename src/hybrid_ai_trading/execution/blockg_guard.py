# -*- coding: utf-8 -*-
"""
Compatibility shim.

Some modules import:
  from hybrid_ai_trading.execution.blockg_guard import require_blockg_ready

Institutional rule:
  - Contract semantics are owned by blockg_contract.ensure_symbol_blockg_ready (fail-closed).
  - This shim preserves legacy callers that pass an explicit 'status' dict (tests).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from hybrid_ai_trading.execution.blockg_contract import ensure_symbol_blockg_ready
from hybrid_ai_trading.execution.blockg_enforce import require_blockg_ready_for_live


def require_blockg_ready(symbol: str, status: Optional[Dict[str, Any]] = None) -> None:
    """
    Backwards-compatible name used by older code paths.

    Tighten-only:
      - If a status dict is provided (tests/legacy), delegate to blockg_enforce (no behavior change).
      - Otherwise, delegate to blockg_contract (authority) using default contract path resolution.
    """
    if isinstance(status, dict):
        require_blockg_ready_for_live(symbol=symbol, status=status)
        return

    # Contract authority (fail-closed). allow_paper=True preserves current semantics used across repo.
    ensure_symbol_blockg_ready(str(symbol).upper(), allow_paper=True, is_paper=False, ctx=None)
