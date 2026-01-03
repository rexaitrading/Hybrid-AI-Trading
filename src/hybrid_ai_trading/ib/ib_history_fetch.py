from __future__ import annotations

import argparse
import csv
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# Fail-closed import: IBKR official python client
try:
    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.contract import Contract
except Exception as e:  # pragma: no cover
    raise SystemExit(
        "[ibkr] Missing ibapi dependency. Install IBKR API python package (ibapi) in your venv. "
        f"Import error: {e}"
    )

@dataclass
class Bar:
    ts: str
    open: float
    high: float
    low: float
    close: float
    volume: float

class HistApp(EWrapper, EClient):
    def __init__(self) -> None:
        EClient.__init__(self, self)
        self._bars: List[Bar] = []
        self._done: bool = False
        self._err: Optional[str] = None

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        # IBKR sends many non-fatal "error" callbacks that are warnings / status lines.
        # We must NOT fail-closed on these, otherwise historical bar fetch will delete output.
        try:
            code = int(errorCode)
        except Exception:
            code = -1

        # Non-fatal status / warnings (do not treat as failure)
        non_fatal = {
            2104,  # Market data farm connection is OK
            2106,  # HMDS connection is OK
            2107,  # HMDS connection inactive but available on demand
            2158,  # Sec-def data farm connection is OK
            2176,  # API version fractional share rules warning
        }
        if code in non_fatal:
            return

        # Fail-closed only on real errors
        self._err = f"reqId={reqId} code={code} msg={errorString}"

    def historicalData(self, reqId, bar):
        # bar.date is usually "YYYYMMDD  HH:MM:SS" for intraday
        try:
            ts = str(bar.date)
            self._bars.append(
                Bar(
                    ts=ts,
                    open=float(bar.open),
                    high=float(bar.high),
                    low=float(bar.low),
                    close=float(bar.close),
                    volume=float(bar.volume),
                )
            )
        except Exception:
            # ignore malformed bar, but keep running
            return

    def historicalDataEnd(self, reqId, start, end):
        self._done = True

def _contract_stock(symbol: str) -> Contract:
    c = Contract()
    c.symbol = symbol.upper()
    c.secType = "STK"
    c.exchange = "SMART"
    c.currency = "USD"
    return c

def fetch_1m_bars(
    symbol: str,
    as_of_date: str,  # YYYY-MM-DD
    host: str,
    port: int,
    client_id: int,
    use_rth: bool,
    out_csv: Path,
    timeout_s: int = 60,
) -> int:
    # IB expects endDateTime as "YYYYMMDD HH:MM:SS TZ"
    # Use US/Eastern close time for RTH; still works for useRTH=0
    ymd = as_of_date.replace("-", "")
    end_dt = f"{ymd} 16:00:00 US/Eastern"

    app = HistApp()
    app.connect(host, port, client_id)

    # Spin network loop in background thread
    app_thread_started = False
    try:
        import threading
        t = threading.Thread(target=app.run, daemon=True)
        t.start()
        app_thread_started = True

        # Wait for connection handshake
        # (ibapi doesn't give a clean "connected" callback; small delay is pragmatic)
        time.sleep(0.8)

        req_id = 9001
        contract = _contract_stock(symbol)

        app.reqHistoricalData(
            reqId=req_id,
            contract=contract,
            endDateTime=end_dt,
            durationStr="1 D",
            barSizeSetting="1 min",
            whatToShow="TRADES",
            useRTH=1 if use_rth else 0,
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[],
        )

        t0 = time.time()
        while not app._done and (time.time() - t0) < timeout_s:
            time.sleep(0.05)

        # Stop subscription cleanly
        try:
            app.cancelHistoricalData(req_id)
        except Exception:
            pass

        if app._err:
            return _fail(out_csv, f"[ibkr] ERROR: {app._err}")

        if not app._bars:
            return _fail(out_csv, "[ibkr] ERROR: no bars returned (check market data permissions / trading day / connection)")

        # Write canonical CSV: ts,open,high,low,close,volume
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["ts", "open", "high", "low", "close", "volume"])
            for b in app._bars:
                w.writerow([b.ts, b.open, b.high, b.low, b.close, b.volume])

        return 0

    finally:
        try:
            if app.isConnected():
                app.disconnect()
        except Exception:
            pass

        # if thread didn't start, nothing else to do
        _ = app_thread_started

def _fail(out_csv: Path, msg: str) -> int:
    # fail-closed: do not create partial bar file
    try:
        if out_csv.exists():
            out_csv.unlink()
    except Exception:
        pass
    print(msg)
    return 2

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--as-of-date", required=True, help="YYYY-MM-DD")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=4002)  # IB Gateway paper default in many setups
    p.add_argument("--client-id", type=int, default=77)
    p.add_argument("--use-rth", action="store_true", help="Regular Trading Hours only")
    p.add_argument("--outdir", default="logs/bars")
    args = p.parse_args()

    repo = Path(__file__).resolve().parents[3]
    outdir = (repo / args.outdir).resolve()
    out_csv = outdir / f"{args.symbol.upper()}_{args.as_of_date}_1m.csv"

    rc = fetch_1m_bars(
        symbol=args.symbol,
        as_of_date=args.as_of_date,
        host=args.host,
        port=args.port,
        client_id=args.client_id,
        use_rth=bool(args.use_rth),
        out_csv=out_csv,
    )
    if rc == 0:
        print("[ibkr] wrote " + out_csv.name)
    return rc

if __name__ == "__main__":
    raise SystemExit(main())