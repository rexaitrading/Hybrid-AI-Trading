# get_news.py â€” UTF-8 (no BOM)
import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone

from ib_insync import IB, Stock


def iso_utc(dt=None):
    return (dt or datetime.now(timezone.utc)).isoformat()


class _ErrCatcher:
    """Capture IB error codes during a guarded call, optionally squelch 321 lines."""

    def __init__(self, ib: IB, squelch_codes=None):
        self.ib = ib
        self.codes = []
        self.squelch = set(squelch_codes or [])

    def __enter__(self):
        self.ib.errorEvent += self._on_err
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self.ib.errorEvent -= self._on_err
        except Exception:
            pass
        return False

    def _on_err(self, reqId, code, msg, advancedOrderRejectJson=None):
        try:
            self.codes.append(int(code))
        except Exception:
            pass
        if code in self.squelch:
            return  # swallow this one silently


def main():
    ap = argparse.ArgumentParser(description="Poll IBKR news for symbols")
    ap.add_argument("symbols", nargs="*", help="Symbols (e.g. AAPL NVDA MSFT)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=4002)
    ap.add_argument("--clientId", type=int, default=106)
    ap.add_argument(
        "--providers",
        default="",
        help="Comma list like BRF,DJNL,FLY; empty=auto-prune by entitlements",
    )
    ap.add_argument(
        "--lookbackMin", type=int, default=30, help="Initial history window (minutes)"
    )
    ap.add_argument(
        "--poll", type=float, default=5.0, help="Poll interval seconds; 0=single run"
    )
    ap.add_argument(
        "--maxResults", type=int, default=50, help="Max historical items per request"
    )
    ap.add_argument(
        "--withBody", action="store_true", help="Fetch full article body (slower)"
    )
    ap.add_argument(
        "--json", action="store_true", help="Emit JSON lines (one object per line)"
    )
    ap.add_argument(
        "--mergeShape",
        action="store_true",
        help='Emit {"ts":..,"news":[...]}, one object then exit',
    )
    args = ap.parse_args()

    syms = args.symbols or ["AAPL"]
    ib = IB()
    try:
        ib.connect(args.host, args.port, clientId=args.clientId, timeout=30)
        if not ib.isConnected():
            print("ERROR: cannot connect to IB API", file=sys.stderr)
            sys.exit(2)

        # Contracts (symbol -> conId)
        contracts = {}
        for s in syms:
            try:
                cds = ib.reqContractDetails(Stock(s, "SMART", "USD")) or []
                if cds:
                    contracts[s] = cds[0].contract.conId
                else:
                    print(f"WARN: no contract for {s}", file=sys.stderr)
            except Exception as e:
                print(f"WARN: contract lookup failed for {s}: {e}", file=sys.stderr)

        if not contracts:
            print("ERROR: no valid contracts", file=sys.stderr)
            sys.exit(3)

        # Providers offered by IB
        try:
            avail = ib.reqNewsProviders() or []
            available_set = {p.code for p in avail}
        except Exception as e:
            available_set = set()
            print(f"WARN: news providers unavailable: {e}", file=sys.stderr)

        # Choose providers
        if args.providers:
            want = {c.strip() for c in args.providers.split(",") if c.strip()}
            prov_codes = sorted(list(want & available_set))
        else:
            prov_codes = sorted(list(available_set))

        # Auto-prune (drop non-entitled providers; silence 321)
        if prov_codes:
            sample_conId = next(iter(contracts.values()))
            start_probe = (datetime.now(timezone.utc) - timedelta(minutes=2)).strftime(
                "%Y%m%d %H:%M:%S"
            )
            end_probe = datetime.now(timezone.utc).strftime("%Y%m%d %H:%M:%S")
            keep = []
            for code in prov_codes:
                try:
                    with _ErrCatcher(ib, squelch_codes={321}):
                        _ = ib.reqHistoricalNews(
                            sample_conId, code, start_probe, end_probe, 1
                        )
                    keep.append(code)  # keep it if no exception was raised
                except Exception:
                    pass
            prov_codes = keep

        # If none left, emit empty payload and exit cleanly
        if not prov_codes:
            payload = {"ts": iso_utc(), "connected": True, "providers": [], "news": []}
            if args.mergeShape:
                print(json.dumps(payload, ensure_ascii=False))
            elif args.json:
                print(
                    json.dumps(
                        {"ts": payload["ts"], "note": "no entitled news providers"},
                        ensure_ascii=False,
                    )
                )
            else:
                print(f"[{payload['ts']}] no entitled news providers")
            return

        seen = set()
        start_ts = datetime.now(timezone.utc) - timedelta(minutes=args.lookbackMin)

        def fetch_batch(window_start, window_end):
            batch = []
            for sym, conId in contracts.items():
                try:
                    items = (
                        ib.reqHistoricalNews(
                            conId,
                            ",".join(prov_codes),
                            window_start.strftime("%Y%m%d %H:%M:%S"),
                            window_end.strftime("%Y%m%d %H:%M:%S"),
                            args.maxResults,
                        )
                        or []
                    )
                except Exception as e:
                    print(
                        f"WARN: historical news failed for {sym}: {e}", file=sys.stderr
                    )
                    continue

                for n in items:
                    key = (sym, n.providerCode, n.articleId)
                    if key in seen:
                        continue
                    seen.add(key)
                    body = None
                    if args.withBody:
                        try:
                            art = ib.reqNewsArticle(n.providerCode, n.articleId)
                            body = getattr(art, "articleText", None)
                        except Exception:
                            body = None
                    batch.append(
                        {
                            "ts": iso_utc(),
                            "symbol": sym,
                            "provider": n.providerCode,
                            "articleId": n.articleId,
                            "time": n.time,  # IBKR server time string
                            "headline": n.headline,
                            "body": body,
                        }
                    )
            return batch

        # One pass
        now = datetime.now(timezone.utc)
        batch = fetch_batch(start_ts, now)

        if args.mergeShape:
            out = {
                "ts": iso_utc(),
                "connected": True,
                "providers": prov_codes,
                "news": batch,
            }
            print(json.dumps(out, ensure_ascii=False))
            return

        def emit(blobs):
            if args.json:
                for it in blobs:
                    print(json.dumps(it, ensure_ascii=False))
            else:
                for it in blobs:
                    print(
                        f"[{it['ts']}] {it['symbol']:>6} {it['provider']} {it['articleId']} :: {it['headline']}"
                    )

        emit(batch)

        # Loop (optional)
        if args.poll and args.poll > 0:
            last = now
            while True:
                time.sleep(args.poll)
                last = last - timedelta(seconds=10)  # slight overlap
                now = datetime.now(timezone.utc)
                emit(fetch_batch(last, now))
                last = now

    finally:
        if ib.isConnected():
            ib.disconnect()


if __name__ == "__main__":
    main()
