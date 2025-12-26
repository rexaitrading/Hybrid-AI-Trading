from __future__ import annotations

"""
Compatibility shim for legacy import path:
  hybrid_ai_trading/execution/algos/twap_executor

Use lazy import to avoid circular-import noise during package init.
"""

from typing import Any

def __getattr__(name: str) -> Any:
    if name == "TWAPExecutor":
        from hybrid_ai_trading.algos.twap import TWAPExecutor  # local import
        return TWAPExecutor
    raise AttributeError(name)
