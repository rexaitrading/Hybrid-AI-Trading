"""
DEPRECATED: Algo Orchestrator (Execution Layer)
(Hybrid AI Quant Pro v3.0 â€“ Backward-Compatible Wrapper)
--------------------------------------------------------

âš ï¸ WARNING:
    This file is deprecated and kept only for backward compatibility.
    Use `hybrid_ai_trading.algos` (orchestrator) instead.

    Example:
        from hybrid_ai_trading.algos import get_algo_executor, VWAPExecutor
"""

import logging
import warnings

# Re-export everything from the canonical orchestrator
from hybrid_ai_trading.algos.orchestrator import (
    ALGO_REGISTRY,
    VWAPSignal,
    get_algo_executor,
    vwap_signal,
)

# Lazily resolve executors (ensures loop-proof imports)
VWAPExecutor = get_algo_executor("VWAP")
TWAPExecutor = get_algo_executor("TWAP")
IcebergExecutor = get_algo_executor("ICEBERG")

__all__ = [
    "get_algo_executor",
    "ALGO_REGISTRY",
    "VWAPExecutor",
    "TWAPExecutor",
    "IcebergExecutor",
    "vwap_signal",
    "VWAPSignal",
]

# ----------------------------------------------------------------------
# Deprecation warning (shows up once per session)
# ----------------------------------------------------------------------
logger = logging.getLogger(__name__)

warnings.warn(
    "hybrid_ai_trading.execution.algos is deprecated. "
    "Use hybrid_ai_trading.algos (orchestrator) instead.",
    DeprecationWarning,
    stacklevel=2,
)
logger.warning(
    "âš ï¸ DEPRECATED: import from execution.algos; use algos.orchestrator instead."
)
