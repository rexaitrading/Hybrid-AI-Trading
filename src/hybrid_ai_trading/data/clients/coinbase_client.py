from __future__ import annotations
"""
Coinbase Advanced Trade Client (Hybrid AI Quant Pro v1.2 – Secure)
- Uses coinbase-advanced-py RESTClient with the new key file format (name + privateKey).
- Robust key-file resolution: explicit arg, env var, cwd/config, repo/config, src/config.

CLI:
  PYTHONPATH=src python .../coinbase_client.py --list-accounts --key-file "<full path to cdp_api_key.json>"
  PYTHONPATH=src python .../coinbase_client.py --ticker BTC-USD
"""

import os
import argparse
from typing import Optional, List
from coinbase.rest import RESTClient


def _candidate_keyfiles(explicit: Optional[str]) -> List[str]:
    cands = []
    if explicit:
        cands.append(os.path.abspath(explicit))
    env = os.getenv("COINBASE_KEYFILE")
    if env:
        cands.append(os.path.abspath(env))

    # cwd/config/cdp_api_key.json
    cands.append(os.path.abspath(os.path.join(os.getcwd(), "config", "cdp_api_key.json")))

    # repo/config: go up from this file to repo root
    here = os.path.dirname(__file__)
    # .../src/hybrid_ai_trading/data/clients -> repo root is four levels up
    cands.append(os.path.abspath(os.path.join(here, "..", "..", "..", "..", "config", "cdp_api_key.json")))
    # also try src/config (in case user stored under src/)
    cands.append(os.path.abspath(os.path.join(here, "..", "..", "..", "config", "cdp_api_key.json")))
    return cands


def _resolve_keyfile(explicit: Optional[str]) -> str:
    for p in _candidate_keyfiles(explicit):
        if p and os.path.exists(p):
            return p
    raise FileNotFoundError(
        "Could not find cdp_api_key.json. "
        "Pass --key-file, or set COINBASE_KEYFILE, or place it under repo\\config\\cdp_api_key.json."
    )


def create_client(key_file: Optional[str] = None) -> RESTClient:
    kf = _resolve_keyfile(key_file)
    return RESTClient(key_file=kf)


def main() -> None:
    ap = argparse.ArgumentParser(description="Coinbase Advanced Trade client quick tests")
    ap.add_argument("--key-file", help="Path to cdp_api_key.json")
    ap.add_argument("--list-accounts", action="store_true", help="List accounts/balances")
    ap.add_argument("--ticker", type=str, help='Product ID, e.g. "BTC-USD"')
    args = ap.parse_args()

    client = create_client(args.key_file)

    if args.list_accounts:
        print(client.get_accounts().to_dict())
        return

    if args.ticker:
        print(client.get_product(args.ticker).to_dict())
        return

    # default public call
    print(client.get_public_products().to_dict())


if __name__ == "__main__":
    main()
