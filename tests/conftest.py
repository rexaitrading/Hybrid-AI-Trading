from __future__ import annotations

import os
import sys
import pathlib
import importlib.util

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]  # repo root (tests/..)

# Ensure repo root + src are importable regardless of CWD
for cand in [ROOT / "src", ROOT]:
    sp = str(cand)
    if sp not in sys.path:
        sys.path.insert(0, sp)

def _mask_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        return "NOT_SET"
    tail = v[-4:] if len(v) >= 4 else v
    return f"SET(****{tail})"

# Never print full secrets; only masked tails for diagnostics
print("OPENAI_API_KEY: " + _mask_env("OPENAI_API_KEY"))
print("COINAPI_KEY: " + _mask_env("COINAPI_KEY"))
print("BROKER_API_KEY: " + _mask_env("BROKER_API_KEY"))

# Diagnostic: is package importable?
spec = importlib.util.find_spec("hybrid_ai_trading")
sys.stderr.write(f"[conftest] exe={sys.executable} importable={bool(spec)} root={ROOT}\n")

# === IB_INSYNC_TEST_SHIM_BEGIN ===
# Minimal ib_insync stub for smoke tests when real package is absent.
try:
    import ib_insync  # type: ignore
except Exception:
    import types

    m = types.ModuleType("ib_insync")

    class _IBDummy:
        def __init__(self, *a, **k):
            pass

        def __call__(self, *a, **k):
            return self

        def __getattr__(self, _):
            return self

    class IB(_IBDummy):
        def connect(self, *a, **k):
            return True

        def disconnect(self, *a, **k):
            return None

    class Contract(_IBDummy):
        pass

    class Stock(_IBDummy):
        pass

    class Forex(_IBDummy):
        pass

    class MarketOrder(_IBDummy):
        pass

    class LimitOrder(_IBDummy):
        pass

    class ContractDetails(_IBDummy):
        pass

    class Ticker(_IBDummy):
        pass

    # Attach into module and register
    m.IB = IB
    m.Contract = Contract
    m.Stock = Stock
    m.Forex = Forex
    m.MarketOrder = MarketOrder
    m.LimitOrder = LimitOrder
    m.ContractDetails = ContractDetails
    m.Ticker = Ticker
    sys.modules["ib_insync"] = m
# === IB_INSYNC_TEST_SHIM_END ===