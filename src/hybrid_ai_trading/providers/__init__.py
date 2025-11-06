<<<<<<< HEAD
import importlib as _imp


def get_price(symbol, cfg):
    return _imp.import_module("hybrid_ai_trading.providers.price").get_price(
        symbol, cfg
    )


def load_providers(path):
    return _imp.import_module("hybrid_ai_trading.providers.price").load_providers(path)


__all__ = ["get_price", "load_providers"]
=======
# Uniform API for tests: always include "symbol" in get_price() output.
from ..providers_basic import get_price as _gp
from ..providers_basic import load_providers as _lp


def load_providers(path: str):
    return _lp(path)


def get_price(symbol: str, cfg):
    try:
        out = _gp(symbol, cfg)
        if not isinstance(out, dict) or "symbol" not in out:
            return {"symbol": symbol, "price": None, "reason": "error"}
        return out
    except Exception:
        return {"symbol": symbol, "price": None, "reason": "error"}
>>>>>>> origin/main
