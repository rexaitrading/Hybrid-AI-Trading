from __future__ import annotations

"""
Compatibility shim for legacy import path:
  hybrid_ai_trading.execution.algos.twap_executor

Re-exports TWAPExecutor from the canonical implementation.
"""

from hybrid_ai_trading.algos.twap import TWAPExecutor  # noqa: F401
