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
