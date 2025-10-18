# -*- coding: utf-8 -*-
from __future__ import annotations
import csv, pathlib, json
from typing import List, Dict, Any, Iterable

def load_csv(path: str) -> Iterable[Dict[str, Any]]:
    p = pathlib.Path(path)
    with p.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            yield row

def row_to_snapshot(row: Dict[str, Any]) -> Dict[str, Any]:
    sym = (row.get("symbol") or row.get("Symbol") or "").strip()
    # pick best price
    def f(x):
        try: return float(x)
        except: return None
    price = f(row.get("price")) or f(row.get("last")) or f(row.get("close")) or f(row.get("vwap"))
    return {
        "symbol": sym,
        "price": price,
        "bid": f(row.get("bid")),
        "ask": f(row.get("ask")),
        "last": f(row.get("last")),
        "close": f(row.get("close")),
        "vwap": f(row.get("vwap")),
        "volume": f(row.get("volume")) or 0.0,
        "ts": row.get("ts") or row.get("timestamp") or row.get("time")
    }