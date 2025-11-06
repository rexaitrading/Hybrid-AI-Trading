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
