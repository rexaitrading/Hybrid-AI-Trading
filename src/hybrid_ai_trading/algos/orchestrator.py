"""
Algo Orchestrator (Hybrid AI Quant Pro v2.6 – Hedge-Fund Grade, Loop-Proof, AAA Coverage)
-----------------------------------------------------------------------------------------

Central orchestrator for algorithmic execution strategies.

Responsibilities
---------------
- Maintain a registry of supported execution algos
- Provide discovery via `get_algo_executor`
- Expose unified imports for VWAP, TWAP, and Iceberg executors
- Wrap signals (VWAPSignal) for strategy-level integration
"""

import logging
from typing import Any, Dict, Type

from hybrid_ai_trading.signals.vwap import VWAPSignal, vwap_signal

# ⚠️ NOTE: Do not import VWAPExecutor/TWAPExecutor/IcebergExecutor at top level to avoid circular imports.

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ----------------------------------------------------------------------
# Lazy import helpers (defer heavy imports until needed)
# ----------------------------------------------------------------------
def _load_vwap_executor() -> Any:
    from hybrid_ai_trading.algos.vwap_executor import VWAPExecutor

    return VWAPExecutor


def _load_twap_executor() -> Any:
    from hybrid_ai_trading.algos.twap import TWAPExecutor

    return TWAPExecutor


def _load_iceberg_executor() -> Any:
    from hybrid_ai_trading.algos.iceberg import IcebergExecutor

    return IcebergExecutor


# ----------------------------------------------------------------------
# Algo Registry
# ----------------------------------------------------------------------
ALGO_REGISTRY: Dict[str, Any] = {
    "VWAP": _load_vwap_executor,
    "TWAP": _load_twap_executor,
    "ICEBERG": _load_iceberg_executor,
}


def get_algo_executor(name: str) -> Type:
    """
    Retrieve an algo executor class by name.

    Parameters
    ----------
    name : str
        Name of the execution algo ("VWAP", "TWAP", "ICEBERG")

    Returns
    -------
    Type
        The executor class (not an instance).
    """
    key = name.strip().upper()
    if key not in ALGO_REGISTRY:
        logger.error("Algo executor not found: %s", name)
        raise KeyError(f"Algo executor '{name}' not found")

    # Call the loader to fetch the class; do not instantiate here
    return ALGO_REGISTRY[key]()


__all__ = [
    "ALGO_REGISTRY",
    "get_algo_executor",
    "vwap_signal",
    "VWAPSignal",
]
