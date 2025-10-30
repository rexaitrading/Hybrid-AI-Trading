from __future__ import annotations

"""
IBKR Executor (Hybrid AI Quant Pro v1.0 - DRY-RUN Safe)
- Dry-run by default; --live requires env IBKR_LIVE=1
- Market and limit stock orders; cancel-all path
- Connects to paper TWS by default (127.0.0.1:7497)
"""

import argparse
import json
import os
import sys

from ib_insync import IB

from hybrid_ai_trading.data.clients.ibkr_client import (
    cancel_all,
    connect_ib,
    place_limit_stock,
    place_market_stock,
)


def _require_live(args: argparse.Namespace) -> bool:
    if not args.live:
        return False
    if os.getenv("IBKR_LIVE", "0") != "1":
        print("Refusing LIVE: set IBKR_LIVE=1 to enable IBKR orders.", file=sys.stderr)
        sys.exit(2)
    return True


def _print(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=True))


def main() -> None:
    ap = argparse.ArgumentParser(description="IBKR executor (DRY-RUN by default)")
    ap.add_argument("--symbol", type=str, default="AAPL")
    ap.add_argument("--market-buy-shares", type=float)
    ap.add_argument("--market-sell-shares", type=float)
    ap.add_argument("--limit-buy-shares", type=float)
    ap.add_argument("--limit-sell-shares", type=float)
    ap.add_argument("--limit-price", type=float)
    ap.add_argument("--cancel-all", action="store_true")
    ap.add_argument("--live", action="store_true", help="Requires IBKR_LIVE=1")
    args = ap.parse_args()

    ib: IB = connect_ib(readonly=not args.live)

    try:
        if args.cancel_all:
            if _require_live(args):
                _print(cancel_all(ib, args.symbol))
            else:
                _print({"dry_run": True, "op": "cancel_all", "symbol": args.symbol})
            return

        # Market BUY
        if args.market_buy_shares is not None:
            if _require_live(args):
                _print(
                    place_market_stock(ib, args.symbol, args.market_buy_shares, "BUY")
                )
            else:
                _print(
                    {
                        "dry_run": True,
                        "op": "market_buy",
                        "symbol": args.symbol,
                        "shares": args.market_buy_shares,
                    }
                )
            return

        # Market SELL
        if args.market_sell_shares is not None:
            if _require_live(args):
                _print(
                    place_market_stock(ib, args.symbol, args.market_sell_shares, "SELL")
                )
            else:
                _print(
                    {
                        "dry_run": True,
                        "op": "market_sell",
                        "symbol": args.symbol,
                        "shares": args.market_sell_shares,
                    }
                )
            return

        # Limit BUY
        if args.limit_buy_shares is not None:
            price = float(args.limit_price) if args.limit_price is not None else None
            if price is None:
                _print({"error": "limit_price required for limit-buy"})
                return
            if _require_live(args):
                _print(
                    place_limit_stock(
                        ib, args.symbol, args.limit_buy_shares, price, "BUY"
                    )
                )
            else:
                _print(
                    {
                        "dry_run": True,
                        "op": "limit_buy",
                        "symbol": args.symbol,
                        "shares": args.limit_buy_shares,
                        "limit_price": price,
                    }
                )
            return

        # Limit SELL
        if args.limit_sell_shares is not None:
            price = float(args.limit_price) if args.limit_price is not None else None
            if price is None:
                _print({"error": "limit_price required for limit-sell"})
                return
            if _require_live(args):
                _print(
                    place_limit_stock(
                        ib, args.symbol, args.limit_sell_shares, price, "SELL"
                    )
                )
            else:
                _print(
                    {
                        "dry_run": True,
                        "op": "limit_sell",
                        "symbol": args.symbol,
                        "shares": args.limit_sell_shares,
                        "limit_price": price,
                    }
                )
            return

        # default: dry-run hint
        _print(
            {
                "hint": "use --market-buy-shares / --market-sell-shares / --limit-* options",
                "symbol": args.symbol,
            }
        )

    finally:
        ib.disconnect()


if __name__ == "__main__":
    main()
