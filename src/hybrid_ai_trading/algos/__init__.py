"""
Hybrid AI Quant Pro â€“ Algo Executors (Hedge-Fund OE Grade, Loop-Proof)
----------------------------------------------------------------------
Central orchestrator for execution algorithms.

Exports:
- VWAPExecutor
- TWAPExecutor
- IcebergExecutor
- vwap_signal, VWAPSignal
- get_algo_executor, ALGO_REGISTRY
"""

from .orchestrator import ALGO_REGISTRY, VWAPSignal, get_algo_executor, vwap_signal

# ----------------------------------------------------------------------
# Re-export executor classes for direct imports
# (Resolved once at module import, using orchestrator lazy-loaders)
# ----------------------------------------------------------------------
VWAPExecutor = get_algo_executor("VWAP")
TWAPExecutor = get_algo_executor("TWAP")
IcebergExecutor = get_algo_executor("ICEBERG")

# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
__all__ = [
    "get_algo_executor",
    "ALGO_REGISTRY",
    "VWAPExecutor",
    "TWAPExecutor",
    "IcebergExecutor",
    "vwap_signal",
    "VWAPSignal",
]
