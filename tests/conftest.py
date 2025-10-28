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
# Minimal ib_insync stub for smoke tests when real package is absent.
try:
    import ib_insync  # type=ignore
except Exception:
    import sys, types
    m = types.ModuleType("ib_insync")
    class _IBDummy:
        def __init__(self,*a,**k): pass
        def __call__(self,*a,**k): return self
        def __getattr__(self, _): return self
    class IB(_IBDummy):
        def connect(self,*a,**k): return True
        def disconnect(self,*a,**k): return None
    class Contract(_IBDummy): pass
    class Stock(_IBDummy):   pass
    class Forex(_IBDummy):   pass
    class MarketOrder(_IBDummy): pass
    class LimitOrder(_IBDummy):  pass
    class ContractDetails(_IBDummy): pass
    class Ticker(_IBDummy):       pass
    class util(_IBDummy):         pass
    m.IB=IB; m.Contract=Contract; m.Stock=Stock; m.Forex=Forex
    m.MarketOrder=MarketOrder; m.LimitOrder=LimitOrder; m.ContractDetails=ContractDetails; m.Ticker=Ticker; m.util=util
    def _ibins_getattr(name):  # catch-all for any other symbol (Order, TagValue, etc.)
        return _IBDummy()
    m.__getattr__ = _ibins_getattr
    sys.modules["ib_insync"] = m
# === IB_INSYNC_TEST_SHIM_END ===



