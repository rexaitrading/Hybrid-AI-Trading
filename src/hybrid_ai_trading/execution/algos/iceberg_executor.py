from __future__ import annotations

"""
Compatibility shim for legacy import path:
  hybrid_ai_trading.execution.algos.iceberg_executor

Re-exports IcebergExecutor from the canonical implementation.
"""

from hybrid_ai_trading.algos.iceberg import IcebergExecutor  # noqa: F401
