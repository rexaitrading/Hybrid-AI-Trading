"""
Hedge-Fund OE Grade Connectivity Test
-------------------------------------
- Validates provider connectivity.
- Prints console-friendly output.
- Writes structured JSON logs with timestamps to logs/connectivity.log
- Final SUMMARY (OK / WARN / ERR) + notes for quick triage
"""

from dotenv import load_dotenv
import os, requests, ccxt, json, datetime, math, re
from pathlib import Path

def _is_nan(x): return isinstance(x, float) and math.isnan(x)

def safe_print(name, fn, bucket):
    rec = {"provider": name, "status": "ERR", "result": None, "error": None, "warn": None}
    try:
        out = fn()
        meta = None
        if isinstance(out, tuple):
            result, meta = out
        else:
            result = out
        print(f"{name:20} OK  {result}")
        rec["status"] = "OK"
        rec["result"] = str(result)
        if isinstance(meta, dict) and meta.get("warn"):
            rec["warn"] = meta["warn"]
    except Exception as e:
        print(f"{name:20} ERR {type(e).__name__}: {e}")
        rec["error"] = f"{type(e).__name__}: {e}"
    bucket.append(rec)

if __name__ == "__main__":
    load_dotenv(override=True)
    print("\n=== Provider Connectivity Test ===\n")

    results = []
    ts = datetime.datetime.now(datetime.UTC).isoformat()

    # --------------- Kraken ---------------
    def test_kraken():
        kr = ccxt.kraken({"apiKey": os.getenv("KRAKEN_API_KEY"), "secret": os.getenv("KRAKEN_PRIVATE_KEY")})
        bal = kr.fetch_balance()
        assets = [k for k,v in (bal.get("total") or {}).items() if v] or list((bal.get("total") or {}).keys())[:5]
        return f"assets={assets[:5]}"
    safe_print("Kraken", test_kraken, results)

    # --------------- IBKR -----------------
    def test_ibkr_all():
        from ib_insync import IB, Stock
        host = os.getenv("IB_GATEWAY_HOST","127.0.0.1")
        port = int(os.getenv("IB_GATEWAY_PORT","7497"))
        cid  = int(os.getenv("IB_CLIENT_ID","1"))
        sym  = os.getenv("IB_TEST_SYMBOL","AAPL")
        exch = os.getenv("IB_TEST_EXCHANGE","SMART")
        ccy  = os.getenv("IB_TEST_CURRENCY","USD")
        prim = os.getenv("IB_PRIMARY_EXCHANGE","NASDAQ")
        mktType = int(os.getenv("IB_MARKETDATA_TYPE","3"))  # 1=live, 3=delayed

        ib = IB(); ib.connect(host, port, clientId=cid, timeout=10); ib.reqMarketDataType(mktType)

        summary = {r.tag: r.value for r in ib.accountSummary()}
        equity  = summary.get("NetLiquidation") or summary.get("TotalCashValue")
        cash    = summary.get("AvailableFunds") or summary.get("TotalCashValue")

        contract = Stock(sym, exch, ccy, primaryExchange=prim)
        ticker = ib.reqMktData(contract, "", True, False)
        ib.sleep(2.0)
        price = None; warn_meta = None
        try:
            price = ticker.marketPrice()
        except Exception:
            price = getattr(ticker, "last", None) or getattr(ticker, "close", None)

        # Fallback: historical last close if price is None/NaN
        if price is None or _is_nan(price):
            bars = ib.reqHistoricalData(contract, endDateTime="", durationStr="1 D",
                                        barSizeSetting="1 day", whatToShow="TRADES",
                                        useRTH=True, keepUpToDate=False)
            if bars:
                price = bars[-1].close
                warn_meta = {"warn": "ibkr_fallback"}  # mark WARN for summary

        ib.disconnect()
        env_kind = "Paper" if port == 7497 else "Live"
        return (f"{env_kind} eq={equity} cash={cash} {sym} price={price}", warn_meta)
    safe_print("IBKR", test_ibkr_all, results)

    # --------------- Polygon --------------
    def test_polygon():
        key = os.getenv("POLYGON_API_KEY") or ""
        url = f"https://api.polygon.io/v2/aggs/ticker/AAPL/prev?apiKey={key}"
        r = requests.get(url, timeout=12); r.raise_for_status()
        data = r.json()
        return f"AAPL prev close={data.get('results',[{}])[0].get('c')}"
    safe_print("Polygon", test_polygon, results)

    # --------------- CoinDesk (CC) --------
    def test_coindesk():
        key = os.getenv("CRYPTCOMPARE_KEY") or ""
        trials = [("sda","XBX-USD"), ("sda","BTC-USD"), ("cadli","BTC-USD")]
        last_err = None
        for market, inst in trials:
            url = f"https://data-api.coindesk.com/index/cc/v1/latest/tick?market={market}&instruments={inst}&apikey={key}"
            r = requests.get(url, timeout=12)
            if r.status_code == 200:
                d = r.json().get("Data",{}).get(inst)
                if d and "VALUE" in d: return f"{inst}@{market}={d['VALUE']}"
                last_err = f"unexpected payload: {r.text[:160]}"
            else:
                last_err = f"{r.status_code} {r.reason}: {r.text[:160]}"
        raise RuntimeError(last_err or "no valid CoinDesk response")
    safe_print("CoinDesk(CC)", test_coindesk, results)

    # --------------- Alpaca (paper) -------
    def test_alpaca():
        from alpaca.trading.client import TradingClient
        pk, ps = os.getenv("PAPER_NEW_KEY"), os.getenv("PAPER_NEW_SECRET")
        if not pk or not ps: raise RuntimeError("Paper keys missing: set PAPER_NEW_KEY and PAPER_NEW_SECRET in .env")
        client = TradingClient(pk, ps, paper=True)
        acct = client.get_account()
        return f"paper=True equity={acct.equity} cash={acct.cash}"
    safe_print("Alpaca", test_alpaca, results)

    # --------------- Presence checks ------
    for k in ["BENZINGA_API_KEY","COINAPI_KEY","CMEGROUP_TOKEN","CMEGROUP_ACCESS_CODE","OPENAI_API_KEY"]:
        status = "present" if os.getenv(k) else "missing"
        print(f"{k:20} {status}")
        results.append({"provider": k, "status": status, "result": None, "error": None, "warn": None})

    # --------------- SUMMARY --------------
    errs  = [r for r in results if r["status"] in ("ERR","missing")]
    warns = [r for r in results if r.get("warn")]
    oks   = [r for r in results if r["status"] in ("OK","present")]

    overall = "OK"
    if errs: overall = "ERR"
    elif warns: overall = "WARN"

    notes = []
    if any(r.get("warn") == "ibkr_fallback" for r in results): notes.append("IBKR market data fallback used")
    # More helpful notes for common errors:
    for r in results:
        if r["provider"] == "Alpaca" and r["error"] and "unauthorized" in r["error"].lower():
            notes.append("Alpaca unauthorized (check PAPER_NEW_KEY/SECRET)")
        if r["provider"] == "Kraken" and r["error"] and "permission" in r["error"].lower():
            notes.append("Kraken permission denied (enable Query Funds)")

    print("\nSUMMARY: {} | ok={} warn={} err={}{}".format(
        overall, len(oks), len(warns), len(errs), (" | notes: " + ", ".join(sorted(set(notes)))) if notes else ""
    ))

    # --------------- Structured log --------
    entry = {"timestamp": ts,
             "summary": {"overall": overall, "ok": len(oks), "warn": len(warns), "err": len(errs), "notes": sorted(set(notes))},
             "results": results}
    with Path("logs/connectivity.log").open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    print("\nDone.\n")
