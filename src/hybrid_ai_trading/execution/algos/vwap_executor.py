from __future__ import annotations

"""
Compatibility shim for legacy import path:
  hybrid_ai_trading.execution.algos.vwap_executor

Use lazy import to avoid circular-import noise during package init.
"""

from typing import Any

def __getattr__(name: str) -> Any:
    if name == "VWAPExecutor":
        from hybrid_ai_trading.algos.vwap_executor import VWAPExecutor  # local import
        return VWAPExecutor
    raise AttributeError(name)
