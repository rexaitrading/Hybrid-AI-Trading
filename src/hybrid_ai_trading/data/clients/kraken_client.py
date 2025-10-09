from __future__ import annotations
"""
Kraken Client (Hybrid AI Quant Pro v1.3 - Explicit Key Resolution)
------------------------------------------------------------------
- _resolve_keyfile: explicit param OR KRAKEN_KEYFILE only (no fallbacks)
- load_client: reads JSON, errors clearly on empty/missing fields
- Exports _resolve_keyfile for tests
"""

import os
import json
import argparse
import ccxt
from typing import Optional


__all__ = ["_resolve_keyfile", "load_client"]


def _resolve_keyfile(explicit: Optional[str]) -> str:
    """
    Resolution contract for tests:
    - If explicit path provided -> must exist, else FileNotFoundError.
    - Else use env KRAKEN_KEYFILE -> must exist, else FileNotFoundError.
    - Else raise FileNotFoundError.
    """
    if explicit:
        p = os.path.abspath(explicit)
        if os.path.exists(p):
            return p
        raise FileNotFoundError(p)

    env = os.getenv("KRAKEN_KEYFILE")
    if env:
        p = os.path.abspath(env)
        if os.path.exists(p):
            return p
        raise FileNotFoundError(p)

    raise FileNotFoundError("KRAKEN_KEYFILE not set and no key_file provided")


def load_client(key_file: Optional[str] = None):
    cfg = _resolve_keyfile(key_file)
    with open(cfg, "rb") as f:
        raw = f.read()
    if not raw.strip():
        raise ValueError(f"Config file {cfg} is empty or unreadable (0 bytes).")
    creds = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(creds, dict) or not creds.get("key") or not creds.get("secret"):
        raise ValueError(f"Config file {cfg} is missing 'key' or 'secret'.")
    return ccxt.kraken({"apiKey": creds["key"], "secret": creds["secret"]})


def main() -> None:
    ap = argparse.ArgumentParser(description="Kraken client quick tests")
    ap.add_argument("--key-file", help="Path to kraken_api.json")
    ap.add_argument("--balance", action="store_true", help="Fetch balances")
    ap.add_argument("--ticker", type=str, help='Get ticker, e.g. "BTC/USDC"')
    args = ap.parse_args()

    client = load_client(args.key_file)

    if args.balance:
        print(client.fetch_balance())
        return
    if args.ticker:
        print(client.fetch_ticker(args.ticker))
        return

    markets = client.load_markets()
    print(f"Loaded {len(markets)} markets")


if __name__ == "__main__":
    main()
