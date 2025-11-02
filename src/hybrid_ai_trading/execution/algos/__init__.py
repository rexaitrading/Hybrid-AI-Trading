import warnings as _w


def _emit():
    _w.warn(
        "deprecated: hybrid_ai_trading.execution.algos  use concrete algo modules directly",
        category=Warning,
        stacklevel=2,
    )


try:
    del __warningregistry__
except Exception:
    pass
_w.simplefilter("always")
_emit()

# Exports (safe placeholders if deps missing)
try:
    from hybrid_ai_trading.execution.algos.iceberg_executor import IcebergExecutor
    from hybrid_ai_trading.execution.algos.twap_executor import TWAPExecutor
    from hybrid_ai_trading.execution.algos.vwap_executor import VWAPExecutor
    from hybrid_ai_trading.signals.vwap import VWAPSignal, vwap_signal
except Exception:

    class VWAPExecutor: ...

    class TWAPExecutor: ...

    class IcebergExecutor: ...

    def vwap_signal(*a, **k):
        return "HOLD"

    class VWAPSignal:
        pass


ALGO_REGISTRY = {"VWAP": VWAPExecutor, "TWAP": TWAPExecutor, "ICEBERG": IcebergExecutor}


def get_algo_executor(name: str):
    key = str(name).upper()
    if key not in ALGO_REGISTRY:
        raise KeyError(f"Executor '{name}' not found")
    return ALGO_REGISTRY[key]
