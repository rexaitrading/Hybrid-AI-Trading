import asyncio
import math
import os
import pathlib
import sys
from datetime import datetime, timezone

# Windows selector loop is more reliable for ib_insync networking
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

import yaml
from ib_insync import IB, Stock

from hybrid_ai_trading.utils.edges import decide_signal
from hybrid_ai_trading.utils.exec import gc_stale_orders
from hybrid_ai_trading.utils.feature_store import FeatureStore
from hybrid_ai_trading.utils.risk import intraday_risk_checks

UNIVERSE_FILE = "config/universe_equities.yaml"
POLL_SEC = 0.5


def _nz(x, default=0.0):
    try:
        if x is None:
            return default
        # NaN check: NaN != NaN
        if isinstance(x, float) and (x != x):
            return default
        return x
    except Exception:
        return default


def _nzi(x, default=0):
    v = _nz(x, None)
    try:
        return int(v) if v is not None else default
    except Exception:
        return default


def load_universe():
    with open(UNIVERSE_FILE, "r", encoding="utf-8") as f:
        d = yaml.safe_load(f)
    syms = []
    for it in d.get("symbols", []):
        if isinstance(it, str):
            syms.append(it)
        elif isinstance(it, dict) and "file" in it:
            p = pathlib.Path(it["file"])
            if p.exists():
                syms += [s.strip() for s in p.read_text().splitlines() if s.strip()]
    return syms


async def connect_with_retry(
    ib: IB, host: str, port: int, cid: int, timeout: int = 40, attempts: int = 8
) -> bool:
    for i in range(1, attempts + 1):
        try:
            await ib.connectAsync(host, port, clientId=cid, timeout=timeout)
            # sanity handshake so we know the API finished starting
            await ib.reqCurrentTimeAsync()
            return True
        except Exception as e:
            try:
                ib.disconnect()
            except Exception:
                pass
            wait = min(5 * i, 30)
            print(
                f"[connect] attempt {i}/{attempts} failed: {type(e).__name__} ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â retrying in {wait}s",
                flush=True,
            )
            await asyncio.sleep(wait)
    return False


async def main():
    host = os.getenv("IB_HOST", "127.0.0.1")
    port = int(os.getenv("IB_PORT", "7497"))
    cid = int(os.getenv("IB_CLIENT_ID", os.getenv("CLIENT_ID", "3021")))

    ib = IB()
    ok = await connect_with_retry(ib, host, port, cid, timeout=40, attempts=8)
    if not ok:
        print(
            "[FATAL] could not establish API session; check TWS API settings",
            flush=True,
        )
        return

    # 1=REALTIME, 3=DELAYED
    mdt = int(
        os.getenv("HAT_MARKET_DATA")
        or os.getenv("HAT_MDT")
        or os.getenv("IB_MDT")
        or "3"
    )
    try:
        ib.reqMarketDataType(mdt)
        print(
            "[runner] marketDataType=" + ("REALTIME" if mdt == 1 else "DELAYED"),
            flush=True,
        )
    except Exception:
        pass

    symbols = load_universe()
    print(
        f"[{datetime.now(timezone.utc).isoformat()}Z] boot | host={host}:{port} cid={cid} | syms={len(symbols)}",
        flush=True,
    )

    # Contracts
    contracts = [
        Stock(sym, "SMART", "USD", primaryExchange="NASDAQ") for sym in symbols
    ]

    # Qualify with fallback
    try:
        await ib.qualifyContractsAsync(*contracts)
    except Exception:
        for c in contracts:
            try:
                await ib.qualifyContractsAsync(c)
            except Exception:
                pass

    # Subscribe top-of-book (delayed or realtime per MDT)
    for c in contracts:
        ib.reqMktData(c, "", True, False)

    store = FeatureStore(root="data/feature_store")
    can_trade = mdt == 1 and not os.getenv(
        "HAT_READONLY"
    )  # never place orders when delayed

    def on_tick(tkr):
        try:
            c = tkr.contract
            bid = float(_nz(getattr(tkr, "bid", None), 0.0))
            ask = float(_nz(getattr(tkr, "ask", None), 0.0))
            last = float(_nz(getattr(tkr, "last", None), 0.0))
            bsz = _nzi(getattr(tkr, "bidSize", None), 0)
            asz = _nzi(getattr(tkr, "askSize", None), 0)
            lsz = _nzi(getattr(tkr, "lastSize", None), 0)

            store.write_quote(
                symbol=c.symbol,
                ts=datetime.now(timezone.utc),
                bid=bid,
                ask=ask,
                last=last,
                bidSize=bsz,
                askSize=asz,
                lastSize=lsz,
            )

            if can_trade:
                sig = decide_signal(tkr)
                if getattr(sig, "action", None) and getattr(sig, "order", None):
                    # guard: ignore invalid/non-positive limit prices
                    if getattr(sig.order, "lmtPrice", None) is not None:
                        try:
                            if float(sig.order.lmtPrice) <= 0:
                                return
                        except Exception:
                            return
                    ib.placeOrder(c, sig.order)

        except Exception as e:
            # log and move on; do not let Event loop die
            print(f"[on_tick] {type(e).__name__}: {e}", flush=True)

    # Hook handlers
    for c in contracts:
        ib.ticker(c).updateEvent += on_tick

    try:
        while True:
            await asyncio.sleep(POLL_SEC)
            gc_stale_orders(ib, max_age_sec=60)
            intraday_risk_checks(ib)
    finally:
        ib.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
