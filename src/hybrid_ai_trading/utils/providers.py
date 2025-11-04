from __future__ import annotations

from typing import Dict


def load_providers(path: str) -> Dict[str, str]:
    return {"equity": "polygon", "crypto": "coinapi"}


def get_price(symbol: str, cfg: Dict[str, str]) -> Dict[str, str]:
    sym = (symbol or "").upper()
    if sym.endswith("USD") or "/" in sym:
        return {"source": cfg.get("crypto", "coinapi"), "symbol": sym, "price": 0.0}
    return {"source": cfg.get("equity", "polygon"), "symbol": sym, "price": 0.0}
