from __future__ import annotations

"""
Compatibility shim for legacy import path:
  hybrid_ai_trading/execution/algos/iceberg_executor

Use lazy import to avoid circular-import noise during package init.
"""

from typing import Any

def __getattr__(name: str) -> Any:
    if name == "IcebergExecutor":
        from hybrid_ai_trading.algos.iceberg import IcebergExecutor  # local import
        return IcebergExecutor
    raise AttributeError(name)
