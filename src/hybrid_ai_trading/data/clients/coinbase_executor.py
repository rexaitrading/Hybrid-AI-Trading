from __future__ import annotations

"""
Coinbase Executor (Hybrid AI Quant Pro v1.0 â€“ DRY-RUN Safe)
- Uses coinbase-advanced-py RESTClient.
- Default is DRY-RUN (no real orders). Pass --live to actually place orders.

CLI examples (after setting PYTHONPATH=src and COINBASE_KEYFILE):
  python .../coinbase_executor.py --pair BTC-USD --market-buy-quote 5
  python .../coinbase_executor.py --pair BTC-USD --limit-buy-base 0.0002 --below-percent 5
  python .../coinbase_executor.py --cancel <ORDER_ID>
  python .../coinbase_executor.py --pair BTC-USD --market-buy-quote 5 --live
"""

import argparse
import json
import math
import os
import uuid
from typing import Optional

from coinbase.rest import RESTClient


def _client() -> RESTClient:
    key_file = os.getenv("COINBASE_KEYFILE")
    if not key_file or not os.path.exists(key_file):
        raise FileNotFoundError("Set COINBASE_KEYFILE to your cdp_api_key.json path")
    return RESTClient(key_file=key_file)


def _round_to_increment(value: float, increment: str) -> str:
    inc = float(increment)
    if inc <= 0:
        return str(value)
    steps = math.floor(value / inc)
    return f"{steps * inc:.{len(increment.split('.')[-1]) if '.' in increment else 0}f}"


def _client_order_id() -> str:
    return str(uuid.uuid4())


def get_increments(product: dict) -> tuple[str, str]:
    # base_increment, quote_increment from get_product()
    return product["base_increment"], product["quote_increment"]


def market_buy_quote(
    client: RESTClient, product_id: str, quote_size: float, live: bool
) -> dict:
    # Round the quote_size to quote_increment
    product = client.get_product(product_id)
    _, q_inc = get_increments(product)
    quote_sz = _round_to_increment(float(quote_size), q_inc)
    if not live:
        return {
            "dry_run": True,
            "op": "market_buy_quote",
            "product_id": product_id,
            "quote_size": quote_sz,
        }
    return client.market_order_buy(
        client_order_id=_client_order_id(),
        product_id=product_id,
        quote_size=str(quote_sz),
    )


def limit_buy_gtc(
    client: RESTClient,
    product_id: str,
    base_size: float,
    limit_price: float,
    live: bool,
) -> dict:
    product = client.get_product(product_id)
    b_inc, p_inc = get_increments(product)
    base_sz = _round_to_increment(float(base_size), b_inc)
    limit_px = _round_to_increment(float(limit_price), p_inc)
    if not live:
        return {
            "dry_run": True,
            "op": "limit_buy_gtc",
            "product_id": product_id,
            "base_size": base_sz,
            "limit_price": limit_px,
        }
    return client.limit_order_gtc_buy(
        client_order_id=_client_order_id(),
        product_id=product_id,
        base_size=str(base_sz),
        limit_price=str(limit_px),
    )


def cancel_order(client: RESTClient, order_id: str, live: bool) -> dict:
    if not live:
        return {"dry_run": True, "op": "cancel_order", "order_id": order_id}
    return client.cancel_orders(order_ids=[order_id])


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Coinbase Advanced Trade executor (DRY-RUN by default)"
    )
    ap.add_argument(
        "--pair", default="BTC-USD", help='Product pair like "BTC-USD" or "BTC-USDC"'
    )
    ap.add_argument(
        "--market-buy-quote",
        type=float,
        help="Spend this much quote currency (e.g., 5 USD)",
    )
    ap.add_argument(
        "--limit-buy-base", type=float, help="Buy this base amount (e.g., 0.0002 BTC)"
    )
    ap.add_argument(
        "--below-percent",
        type=float,
        default=5.0,
        help="Limit % below current price (used with --limit-buy-base)",
    )
    ap.add_argument("--limit-price", type=float, help="Override limit price explicitly")
    ap.add_argument("--cancel", type=str, help="Cancel order by order_id")
    ap.add_argument("--live", action="store_true", help="Actually place/cancel orders")
    args = ap.parse_args()

    client = _client()

    if args.cancel:
        out = cancel_order(client, args.cancel, args.live)
        print(json.dumps(out, indent=2))
        return

    if args.market_buy_quote is not None:
        out = market_buy_quote(client, args.pair, args.market_buy_quote, args.live)
        print(json.dumps(out, indent=2))
        return

    if args.limit_buy_base is not None:
        if args.limit_price is None:
            prod = client.get_product(args.pair)
            px = float(prod["price"])
            target = px * (1 - (args.below_percent / 100.0))
            args.limit_price = target
        out = limit_buy_gtc(
            client, args.pair, args.limit_buy_base, args.limit_price, args.live
        )
        print(json.dumps(out, indent=2))
        return

    # Default: show product info and increments
    prod = client.get_product(args.pair)
    print(
        json.dumps(
            {
                "product_id": args.pair,
                "price": prod["price"],
                "base_increment": prod["base_increment"],
                "quote_increment": prod["quote_increment"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
