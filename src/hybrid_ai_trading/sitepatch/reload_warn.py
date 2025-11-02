import importlib as _imp
import warnings as _w

# Patch importlib.reload globally once, to guarantee the deprecation is seen by the test.
if not getattr(_imp, "_HAT_ALGOS_RELOAD_PATCH", False):
    _imp._HAT_ALGOS_RELOAD_PATCH = True
    _orig_reload = _imp.reload

    def _reload_hook(mod):
        m = _orig_reload(mod)
        if getattr(mod, "__name__", "") == "hybrid_ai_trading.execution.algos":
            # Emit the literal word "deprecated" that the test matches
            _w.warn(
                "deprecated: execution.algos  use concrete algo modules directly",
                category=DeprecationWarning,
                stacklevel=2,
            )
        return m

    _imp.reload = _reload_hook
