"""
Deprecated wrapper: hybrid_ai_trading.algos
Emits DeprecationWarning on import and reload, and re-exports real executors/signals.
"""

import logging as _lg
import warnings as _w


def _emit():
    _w.warn(
        "deprecated: hybrid_ai_trading.algos  use concrete algo modules directly",
        category=Warning,
        stacklevel=2,
    )


# make sure warnings aren't suppressed on re-import
try:
    del __warningregistry__
except Exception:
    pass
_w.simplefilter("always")
_emit()

# Re-export real executors/signals from the canonical locations
try:
    from hybrid_ai_trading.execution.algos.iceberg_executor import IcebergExecutor
    from hybrid_ai_trading.execution.algos.twap_executor import TWAPExecutor
    from hybrid_ai_trading.execution.algos.vwap_executor import VWAPExecutor
    from hybrid_ai_trading.signals.vwap import VWAPSignal, vwap_signal
except Exception as _e:  # fallbacks so import never explodes in isolated runs

    class VWAPExecutor: ...

    class TWAPExecutor: ...

    class IcebergExecutor: ...

    def vwap_signal(*a, **k):
        return "HOLD"

    class VWAPSignal: ...

    _w.warn(f"hybrid_ai_trading.algos fallback exports due to: {_e}", RuntimeWarning)

ALGO_REGISTRY = {
    "VWAP": VWAPExecutor,
    "TWAP": TWAPExecutor,
    "ICEBERG": IcebergExecutor,
}


def get_algo_executor(name: str):
    key = str(name).upper()
    if key not in ALGO_REGISTRY:
        _lg.getLogger(__name__).error("Executor '%s' not found", name)
        raise KeyError(f"Executor '{name}' not found")
    return ALGO_REGISTRY[key]


# --- public API surface required by tests ---
__all__ = [
    "VWAPExecutor",
    "TWAPExecutor",
    "IcebergExecutor",
    "VWAPSignal",
    "vwap_signal",
    "get_algo_executor",
]
