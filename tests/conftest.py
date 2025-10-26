# conftest: ensure repo/src is importable in any CI working dir / interpreter
import os, sys, pathlib, importlib.util
ROOT = pathlib.Path(__file__).resolve().parents[1]  # project root (tests/..)
CANDIDATES = [ROOT / "src", ROOT]
for p in CANDIDATES:
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)
spec = importlib.util.find_spec("hybrid_ai_trading")
sys.stderr.write(f"[conftest] exe={sys.executable} importable={bool(spec)} root={ROOT}\\n")
if spec is None:
    # leave path injected; test files also prepend a tiny shim as last resort
    pass


# === IB_INSYNC_TEST_SHIM_BEGIN ===
# In CI/dev without ib_insync installed, provide a minimal stub so modules importing
# "from ib_insync import ..." do not crash during import of helpers used by smoke tests.
try:
    import ib_insync  # type: ignore
except Exception:
    import sys, types
    m = types.ModuleType("ib_insync")
    class _Dummy:
        def __init__(self, *a, **k): pass
        def __call__(self, *a, **k): return None
        def __getattr__(self, _): return self
    class IB(_Dummy):
        def connect(self, *a, **k): return True
        def disconnect(self): return None
    class Stock(_Dummy): pass
    class Contract(_Dummy): pass
    class MarketOrder(_Dummy):
        def __init__(self, *a, **k): pass
    class LimitOrder(_Dummy):
        def __init__(self, *a, **k): pass
    class util: pass
    m.IB = IB; m.Stock = Stock; m.Contract = Contract
    m.MarketOrder = MarketOrder; m.LimitOrder = LimitOrder; m.util = util
    sys.modules["ib_insync"] = m
# === IB_INSYNC_TEST_SHIM_END ===

