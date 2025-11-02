from __future__ import annotations

import importlib as _imp
import warnings as _w


def __getattr__(name: str):
    if name == "algos":
        # Emit deprecation every time the wrapper is accessed through the package
        _w.warn(
            "deprecated: execution.algos  use concrete algo modules directly",
            category=DeprecationWarning,
            stacklevel=2,
        )
        return _imp.import_module(__name__ + ".algos")
    raise AttributeError(name)
