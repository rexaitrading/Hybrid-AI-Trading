<<<<<<< HEAD
# Ensure global reload hook is active in every interpreter (pytest workers included)
# Hard-bind providers API to the canonical implementation and freeze sys.modules entry
import importlib as _imp
import sys as _sys

from .sitepatch import reload_warn as _hat_reload_warn  # noqa: F401

_price = _imp.import_module("hybrid_ai_trading.providers.price")
_pkg = _imp.import_module("hybrid_ai_trading.providers")
_pkg.get_price = _price.get_price
_pkg.load_providers = _price.load_providers
_sys.modules["hybrid_ai_trading.providers"] = _pkg
=======
# Package-level safety net:
# - Ensure any import path (bare "providers_basic" OR "hybrid_ai_trading.providers_basic")
#   resolves to our safe stub that ALWAYS returns a dict with "symbol".
try:
    import sys

    from . import providers_basic as _pb

    def _safe_get_price(symbol: str, cfg):
        try:
            out = _pb.get_price(symbol, cfg)
            if not isinstance(out, dict) or "symbol" not in out:
                return {"symbol": symbol, "price": None, "reason": "error"}
            return out
        except Exception:
            return {"symbol": symbol, "price": None, "reason": "error"}

    # Patch once
    if getattr(_pb, "_patched_symbol_guard", False) is not True:
        _pb.get_price = _safe_get_price  # type: ignore
        _pb._patched_symbol_guard = True

    # --- CRITICAL ALIAS ---
    # Make bare-name imports ('import providers_basic') resolve to our module
    sys.modules.setdefault("providers_basic", _pb)

except Exception:
    # Safe minimal fallback if anything above fails
    import types

    def _fallback_get_price(symbol: str, cfg):
        return {"symbol": symbol, "price": None, "reason": "error"}

    providers_basic = types.SimpleNamespace(get_price=_fallback_get_price)  # type: ignore
>>>>>>> origin/main
