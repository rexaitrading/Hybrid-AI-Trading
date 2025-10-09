from __future__ import annotations

"""
Kraken Executor (Hybrid AI Quant Pro v1.3 - DRY-RUN Safe + Guards + LiveGuard + Logging)
- Dry-run by default; live only with --live and env KRAKEN_LIVE=1
- Reads keys from env KRAKEN_KEYFILE -> {"key": "...", "secret": "..."}
- BTC<->XBT alias handling; precision rounding; min-size/cost guard
- Funds-first guard (prevents cap usage when balance is 0)
- LiveGuard caps (per-trade quote, daily notional, daily trades)
- CSV logging to logs/trades.csv on LIVE orders
- Cancel path
"""

import argparse
import csv
import json
import os
import sys
import time
from typing import Dict

import ccxt

from hybrid_ai_trading.data.clients.live_guard import check as lg_check


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


def resolve_symbol(ex: "ccxt.kraken", symbol: str) -> str:
    mkts = ex.load_markets()
    if symbol in mkts:
        return symbol
    if symbol.startswith("BTC/"):
        alt = "XBT/" + symbol.split("/", 1)[1]
        if alt in mkts:
            return alt
    if symbol.startswith("XBT/"):
        alt = "BTC/" + symbol.split("/", 1)[1]
        if alt in mkts:
            return alt
    return ex.market(symbol)["symbol"]


def round_amount(ex: "ccxt.kraken", symbol: str, amt: float) -> float:
    return float(ex.amount_to_precision(symbol, amt))


def round_price(ex: "ccxt.kraken", symbol: str, px: float) -> float:
    return float(ex.price_to_precision(symbol, px))


def require_live(args: argparse.Namespace) -> bool:
    if not args.live:
        return False
    if os.getenv("KRAKEN_LIVE", "0") != "1":
        print(
            "Refusing LIVE: set KRAKEN_LIVE=1 to enable live orders.", file=sys.stderr
        )
        sys.exit(2)
    return True


def min_requirements(ex: "ccxt.kraken", symbol: str, last: float) -> Dict[str, float]:
    m = ex.market(symbol)
    lims = m.get("limits", {}) if isinstance(m, dict) else {}
    min_base = float(((lims.get("amount") or {}).get("min")) or 0.0)
    min_cost = float(((lims.get("cost") or {}).get("min")) or 0.0)
    req_quote = max(min_cost, min_base * last if min_base else 0.0)
    return {"min_base": min_base, "min_cost": min_cost, "req_quote": req_quote}


def available_quote(ex: "ccxt.kraken", symbol: str) -> float:
    m = ex.market(symbol)
    quote = (m.get("quote") if isinstance(m, dict) else symbol.split("/", 1)[1]).upper()
    bal = ex.fetch_balance() or {}
    free = bal.get("free") or {}
    try:
        return float(free.get(quote, 0) or 0.0)
    except Exception:
        return 0.0


def log_trade(
    side: str, typ: str, symbol: str, base_amt: float, price: float | None, resp: dict
) -> None:
    try:
        logs_dir = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs")
        )
        os.makedirs(logs_dir, exist_ok=True)
        fp = os.path.join(logs_dir, "trades.csv")
        with open(fp, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                    "kraken",
                    side,
                    typ,
                    symbol,
                    f"{base_amt:.8f}",
                    "" if price is None else f"{price:.2f}",
                    json.dumps(resp),
                ]
            )
    except Exception:
        pass


def main() -> None:
    ap = argparse.ArgumentParser(description="Kraken executor (DRY-RUN by default)")
    ap.add_argument(
        "--symbol",
        default="BTC/USDC",
        help='e.g. "BTC/USDC" (Kraken may map BTC->XBT internally)',
    )
    ap.add_argument(
        "--market-buy-quote", type=float, help="Spend this much quote currency"
    )
    ap.add_argument("--limit-buy-base", type=float, help="Buy this base amount")
    ap.add_argument(
        "--below-percent",
        type=float,
        default=5.0,
        help="Limit % below current if --limit-buy-base",
    )
    ap.add_argument("--limit-price", type=float, help="Explicit limit price override")
    ap.add_argument("--cancel", type=str, help="Cancel order by id")
    ap.add_argument(
        "--live",
        action="store_true",
        help="Actually send orders (requires KRAKEN_LIVE=1)",
    )
    args = ap.parse_args()

    ex = load_client()
    symbol = resolve_symbol(ex, args.symbol)
    ex.load_markets()
    ticker = ex.fetch_ticker(symbol)
    last = (
        float(ticker["last"])
        if ticker.get("last")
        else float((ticker.get("info") or {}).get("c", [0])[0])
    )

    # cancel path
    if args.cancel:
        if require_live(args):
            print(ex.cancel_order(args.cancel, symbol))
        else:
            print(
                {
                    "dry_run": True,
                    "op": "cancel_order",
                    "id": args.cancel,
                    "symbol": symbol,
                }
            )
        return

    mins = min_requirements(ex, symbol, last)

    # market by quote
    if args.market_buy_quote is not None:
        if args.market_buy_quote < mins["req_quote"]:
            print(
                {
                    "error": "below_exchange_minimum",
                    "symbol": symbol,
                    "required_quote_min": round(mins["req_quote"], 4),
                    "hint": f"Try --market-buy-quote {round(mins['req_quote'] + 0.2, 2)} or higher",
                    "ref_px": last,
                }
            )
            return
        base_amt = round_amount(ex, symbol, args.market_buy_quote / last)
        if require_live(args):
            # 1) funds-first
            avail = available_quote(ex, symbol)
            if args.market_buy_quote > avail:
                print(
                    {
                        "error": "insufficient_funds",
                        "symbol": symbol,
                        "required_quote": round(args.market_buy_quote, 4),
                        "available_quote": round(avail, 4),
                    }
                )
                return
            # 2) LiveGuard
            guard = lg_check(
                {
                    "broker": "kraken",
                    "symbol": symbol,
                    "side": "BUY",
                    "notional_quote": float(args.market_buy_quote),
                    "shares": None,
                }
            )
            if not guard.get("ok", True):
                print(guard)
                return
            # 3) place and log
            resp = ex.create_order(symbol, "market", "buy", base_amt)
            print(resp)
            log_trade("BUY", "MKT", symbol, base_amt, None, resp)
        else:
            print(
                {
                    "dry_run": True,
                    "op": "market_buy",
                    "symbol": symbol,
                    "quote_spend": args.market_buy_quote,
                    "approx_base": base_amt,
                    "ref_px": last,
                }
            )
        return

    # limit by base size
    if args.limit_buy_base is not None:
        if args.limit_buy_base < mins["min_base"]:
            print(
                {
                    "error": "below_exchange_minimum",
                    "symbol": symbol,
                    "required_base_min": mins["min_base"],
                    "hint": f"Try --limit-buy-base {mins['min_base']}",
                    "ref_px": last,
                }
            )
            return
        price = (
            args.limit_price
            if args.limit_price is not None
            else last * (1 - args.below_percent / 100.0)
        )
        price = round_price(ex, symbol, price)
        base_amt = round_amount(ex, symbol, args.limit_buy_base)
        if require_live(args):
            # 1) funds-first estimate for limit
            notional = float(base_amt) * float(price)
            avail = available_quote(ex, symbol)
            if notional > avail:
                print(
                    {
                        "error": "insufficient_funds",
                        "symbol": symbol,
                        "required_quote": round(notional, 4),
                        "available_quote": round(avail, 4),
                    }
                )
                return
            # 2) LiveGuard
            guard = lg_check(
                {
                    "broker": "kraken",
                    "symbol": symbol,
                    "side": "BUY",
                    "notional_quote": notional,
                    "shares": None,
                }
            )
            if not guard.get("ok", True):
                print(guard)
                return
            # 3) place and log
            resp = ex.create_order(symbol, "limit", "buy", base_amt, price)
            print(resp)
            log_trade("BUY", "LMT", symbol, base_amt, price, resp)
        else:
            print(
                {
                    "dry_run": True,
                    "op": "limit_buy",
                    "symbol": symbol,
                    "base_size": base_amt,
                    "limit_price": price,
                    "ref_px": last,
                }
            )
        return

    # default: show market info
    m = ex.market(symbol)
    print(
        {
            "symbol": symbol,
            "price": last,
            "precision": m.get("precision", {}),
            "limits": m.get("limits", {}),
        }
    )


if __name__ == "__main__":
    main()
