from __future__ import annotations

"""
Kraken Ops (Hybrid AI Quant Pro v1.0 - Practical Ops Tools)
- --balances
- --open-orders [--symbol]
- --cancel-all  --symbol
- --value       --quote USDC
"""


import argparse
import json
import os
from typing import Any, Dict, List, Optional

import ccxt


def _print_json(obj: Any) -> None:
    """Pretty JSON printer with stable ASCII output."""
    print(json.dumps(obj, indent=2, ensure_ascii=True))


def load_client() -> "ccxt.kraken":
    keyfile = os.getenv("KRAKEN_KEYFILE")
    if not keyfile or not os.path.exists(keyfile):
        raise FileNotFoundError("Set KRAKEN_KEYFILE to your kraken_api.json path")
    with open(keyfile, "rb") as f:
        raw = f.read()
    if not raw.strip():
        raise ValueError(f"Config file {keyfile} is empty")
    creds = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(creds, dict) or not creds.get("key") or not creds.get("secret"):
        raise ValueError(f"Config file {keyfile} missing 'key' or 'secret'")
    return ccxt.kraken({"apiKey": creds["key"], "secret": creds["secret"]})


def balances(ex: "ccxt.kraken") -> None:
    _print_json(ex.fetch_balance())


def open_orders(ex: "ccxt.kraken", symbol: Optional[str]) -> None:
    if symbol:
        _print_json(ex.fetch_open_orders(symbol))
    else:
        _print_json(ex.fetch_open_orders())


def cancel_all(ex: "ccxt.kraken", symbol: str) -> None:
    """Cancel all open orders for a symbol."""
    orders = ex.fetch_open_orders(symbol)
    ids: List[str] = [str(o.get("id")) for o in orders if o.get("id")]
    if not ids:
        _print_json({"canceled": [], "note": "no open orders"})
        return
    for oid in ids:
        ex.cancel_order(oid, symbol)
    _print_json({"canceled": ids})


def value_snapshot(ex: "ccxt.kraken", quote: str) -> None:
    """Portfolio value in a chosen quote (e.g., USDC)."""
    bal = ex.fetch_balance() or {}
    free: Dict[str, Any] = bal.get("free") or {}
    quote = quote.upper()
    total_quote = 0.0
    details: List[Dict[str, Any]] = []
    ex.load_markets()

    for asset, amt in free.items() if isinstance(free, dict) else []:
        try:
            amount = float(amt or 0)
        except Exception:
            continue
        if amount <= 0:
            continue

        if asset.upper() == quote:
            total_quote += amount
            details.append({"asset": asset, "amount": amount, "px": 1.0, "value": amount})
            continue

        pair1 = f"{asset}/{quote}"
        pair2 = f"{quote}/{asset}"
        # Try direct ASSET/QUOTE
        if pair1 in ex.markets:
            t = ex.fetch_ticker(pair1)
            last = t.get("last")
            if last is None:
                last = t.get("info", {}).get("c", [0])[0]
            px = float(last or 0.0)
            val = amount * px
            total_quote += val
            details.append(
                {"asset": asset, "amount": amount, "px": px, "value": val, "pair": pair1}
            )
            continue
        # Try inverse QUOTE/ASSET (convert)
        if pair2 in ex.markets:
            t = ex.fetch_ticker(pair2)
            last = t.get("last")
            if last is None:
                last = t.get("info", {}).get("c", [0])[0]
            px = float(last or 0.0)
            inv_val = amount / px if px else 0.0
            total_quote += inv_val
            details.append(
                {
                    "asset": asset,
                    "amount": amount,
                    "px": px,
                    "value": inv_val,
                    "pair": pair2,
                    "inverse": True,
                }
            )
            continue

        details.append(
            {"asset": asset, "amount": amount, "px": None, "value": None, "note": "no market"}
        )

    _print_json({"quote": quote, "total_value_quote": total_quote, "details": details})


def main() -> None:
    ap = argparse.ArgumentParser(description="Kraken ops helper")
    ap.add_argument("--balances", action="store_true")
    ap.add_argument("--open-orders", action="store_true")
    ap.add_argument("--cancel-all", action="store_true")
    ap.add_argument("--symbol", type=str)
    ap.add_argument("--value", action="store_true")
    ap.add_argument("--quote", type=str, default="USDC")
    args = ap.parse_args()

    ex = load_client()

    if args.balances:
        balances(ex)
        return
    if args.open_orders:
        open_orders(ex, args.symbol)
        return
    if args.cancel_all:
        if not args.symbol:
            _print_json({"error": "provide --symbol for --cancel-all"})
            return
        cancel_all(ex, args.symbol)
        return
    if args.value:
        value_snapshot(ex, args.quote)
        return

    # default: show balances
    balances(ex)


if __name__ == "__main__":
    main()
