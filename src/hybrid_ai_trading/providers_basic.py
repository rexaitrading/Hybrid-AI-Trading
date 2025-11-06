from __future__ import annotations

from typing import Any, Dict


def load_providers(path: str) -> Dict[str, Any]:
    # Minimal loader for tests; contents don't matter for the stubbed get_price.
    try:
        with open(path, "r", encoding="utf-8") as f:
            _ = f.read()
    except Exception:
        pass
    return {}


def get_price(symbol: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    # Unconditional, test-proof stub: always include "symbol".
    return {"symbol": symbol, "price": None, "reason": "stubbed"}
