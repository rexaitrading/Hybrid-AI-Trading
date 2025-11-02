import warnings as _w

# Emit deprecation on every import/reload of the submodule itself (covers importlib.reload)
_w.warn(
    "deprecated: execution.algos  use concrete algo modules directly",
    category=DeprecationWarning,
    stacklevel=2,
)


class VWAPExec:
    pass


class TWAPExec:
    pass


class ICEBERGExec:
    pass


ALGO_REGISTRY = {
    "VWAP": VWAPExec,
    "TWAP": TWAPExec,
    "ICEBERG": ICEBERGExec,
}


def get_algo_executor(name: str):
    key = str(name).upper()
    if key not in ALGO_REGISTRY:
        raise KeyError(f"Unknown algo: {name}")
    return ALGO_REGISTRY[key]
