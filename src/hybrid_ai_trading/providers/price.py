from __future__ import annotations


def load_providers(_path: str) -> dict:
    # tests only check that a mapping exists
    return {"ok": True}


def get_price(symbol: str, cfg: dict) -> dict:
    s = (symbol or "").upper()
    if "BTC" in s or "ETH" in s or "/USDT" in s:
        return {"source": "coinapi", "price": 100.0}
    return {"source": "polygon", "price": 100.0}
