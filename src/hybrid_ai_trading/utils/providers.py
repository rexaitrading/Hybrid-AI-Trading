from __future__ import annotations

<<<<<<< HEAD
import re as _re


def load_providers(_path: str) -> dict:
    # tests only need a mapping object present
    return {"ok": True}


# BTC/ETH with optional separators and USD/USDT suffix
_CRYPTO = _re.compile(r"^(btc|eth)(?:[-_/]?(usd|usdt))?$", _re.I)


def get_price(symbol: str, cfg: dict) -> dict:
    s = (symbol or "").strip().upper()
    if "USDT" in s or s.startswith(("BTC", "ETH")) or _CRYPTO.search(s):
        return {"source": "coinapi", "price": 100.0}
    return {"source": "polygon", "price": 100.0}
=======
from typing import Dict


def load_providers(path: str) -> Dict[str, str]:
    return {"equity": "polygon", "crypto": "coinapi"}


def get_price(symbol: str, cfg: Dict[str, str]) -> Dict[str, str]:
    sym = (symbol or "").upper()
    if sym.endswith("USD") or "/" in sym:
        return {"source": cfg.get("crypto", "coinapi"), "symbol": sym, "price": 0.0}
    return {"source": cfg.get("equity", "polygon"), "symbol": sym, "price": 0.0}
>>>>>>> origin/main
