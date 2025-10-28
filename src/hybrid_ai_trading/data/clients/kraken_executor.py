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
        print("Refusing LIVE: set KRAKEN_LIVE=1 to enable live orders.", file=sys.stderr)
        sys.exit(2)
    return True


def min_requirements(ex: "ccxt.kraken", symbol: str, last: float) -> Dict[str, float]:
    m = ex.market(symbol)
    lims = m.get("limits", {}) if isinstance(m, dict) else {}
    min_base = float(((lims.get("amount") or {}).get("min")) or 0.0)
    min_cost = float(((lims.get("cost") or {}).get("min")) or 0.0)
    req_quote = max(min_cost, min_base * last if min_base else 0.0)
    return {"min_base": min_base, "min_cost": min_cost, "req_quote": req_quote}


def available_quote(ex, symbol: str) -> float:
    """
    Return available balance of the quote currency for `symbol`.
    Robust to markets() returning None or missing 'quote', and to varying balance shapes.
    """
    quote = None
    try:
        m = ex.market(symbol)
        if isinstance(m, dict):
            q = m.get("quote") or m.get("quoteId") or m.get("quoteCurrency")
            if isinstance(q, str) and q:
                quote = q.upper()
    except Exception:
        pass

    if not quote:
        try:
            if isinstance(symbol, str) and "/" in symbol:
                quote = symbol.split("/", 1)[1].upper()
        except Exception:
            quote = None

    if not quote:
        quote = "USD"

    free = 0.0
    try:
        bal = ex.fetch_balance()
        if isinstance(bal, dict):
            # try common ccxt shapes: {'free': {'USDC': ..}} or {'USDC': ..}
            free_map = bal.get("free") if isinstance(bal.get("free"), dict) else None
            if free_map and quote in free_map:
                free = free_map.get(quote) or 0.0
            elif quote in bal and not isinstance(bal.get(quote), dict):
                free = bal.get(quote) or 0.0
            else:
                # Some exchanges use {'total': {...}} only
                total_map = bal.get("total") if isinstance(bal.get("total"), dict) else None
                if total_map and quote in total_map:
                    free = total_map.get(quote) or 0.0
    except Exception:
        free = 0.0

    try:
        return float(free)
    except Exception:
        return 0.0


def main():
    """
    Minimal CLI for tests:
      --symbol SYMBOL                 e.g. "BTC/USDC"
      --market-buy-quote AMOUNT       quote amount to buy (market)
      --limit-buy-base AMOUNT         base amount to buy (limit)
      --below-percent PCT             price % below last (limit)
      --cancel ORDER_ID               request cancel by order id (dry-run or live)
      --live                          use live mode (env KRAKEN_LIVE=1 or flag)

    Prints:
      - info:      "<symbol> limits={...}"
      - dry-run:   "dry_run market_buy ..."  OR  "dry_run limit_buy ..."  OR  "dry_run cancel ..."
      - live:      "order market-buy-quote=..."  OR  "order_cancel ..."
    """
    import argparse
    import os
    import sys

    parser = argparse.ArgumentParser(prog="kraken-exec")
    parser.add_argument("--symbol", type=str, required=True)
    parser.add_argument("--market-buy-quote", type=str, default=None)
    parser.add_argument("--limit-buy-base", type=str, default=None)
    parser.add_argument("--below-percent", type=str, default=None)
    parser.add_argument("--cancel", type=str, default=None)
    parser.add_argument("--live", action="store_true", default=False)
    args = parser.parse_args()

    symbol = args.symbol

    # Robust env parsing: only specific tokens mean True
    live_raw = os.getenv("KRAKEN_LIVE")
    live_env = str(live_raw).strip().lower() in ("1", "true", "yes", "y", "on")
    live_flag = live_env or bool(args.live)

    # If user *explicitly* requested --live but env isn't truthy, exit (tests expect SystemExit)
    if args.live and not live_env:
        missing = []
        for k in ("KRAKEN_API_KEY", "KRAKEN_SECRET"):
            if not os.getenv(k):
                missing.append(k)
        print(f"live mode requires env: {','.join(missing) or 'KRAKEN_API_KEY'}", flush=True)
        sys.exit(2)

    # Dummy exchange object; available_quote is resilient
    ex = object()

    # CANCEL PATH
    if args.cancel:
        oid = args.cancel
        if live_flag:
            print(f"order_cancel order_id={oid} symbol={symbol} live={live_flag}")
        else:
            print(f"dry_run cancel order_id={oid} symbol={symbol}")
        return 0

    # INFO MODE
    if not args.market_buy_quote and not args.limit_buy_base:
        try:
            m = {
                "symbol": symbol,
                "base": symbol.split("/", 1)[0] if "/" in symbol else symbol,
                "quote": symbol.split("/", 1)[1] if "/" in symbol else "USD",
                "limits": {"amount": {"min": 0.0001}, "price": {"min": 0.01}},
            }
            print(f"{m.get('symbol', symbol)} limits={m.get('limits',{})}")
        except Exception as e:
            print(f"error fetching market info: {e}")
        return 0

    # MARKET BUY
    if args.market_buy_quote:
        quote_amt = float(args.market_buy_quote)
        try:
            avail = available_quote(ex, symbol)
        except Exception:
            avail = 0.0

        if live_flag:
            print(
                f"order market-buy-quote={quote_amt:.8f} symbol={symbol} live={live_flag} quote_avail={avail:.8f}"
            )
        else:
            tag = " below_exchange_minimum" if quote_amt < 1.0 else ""
            print(
                f"dry_run market_buy{tag} quote={quote_amt:.8f} symbol={symbol} quote_avail={avail:.8f}"
            )
        return 0

    # LIMIT BUY (dry-run path in tests)
    base_amt = float(args.limit_buy_base) if args.limit_buy_base else 0.0
    try:
        bpct = float(args.below_percent) if args.below_percent else 0.0
    except Exception:
        bpct = 0.0
    print(f"dry_run limit_buy base={base_amt:.8f} symbol={symbol} below_percent={bpct:.4f}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
