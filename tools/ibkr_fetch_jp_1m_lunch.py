import os, sys, time, json, threading
from typing import Optional, List, Dict, Any

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

HOST = os.environ.get("IB_GATEWAY_HOST", "127.0.0.1")
PORT = int(os.environ.get("IB_GATEWAY_PORT", "4002"))
CLIENT_ID = int(os.environ.get("IB_CLIENT_ID", "78"))

REQ_TIMEOUT_SEC = float(os.environ.get("IBKR_REQ_TIMEOUT_SEC", "15"))
CONNECT_TIMEOUT_SEC = float(os.environ.get("IBKR_CONNECT_TIMEOUT_SEC", "6"))

def ymd_to_ib_end(ymd: str, hhmm: str) -> str:
    d = ymd.replace("-", "")
    return f"{d} {hhmm}:00 Asia/Tokyo"


def time_to_yyyymmdd(t: str) -> str:
    s = (t or "").strip()
    # Possible formats:
    #  - "20260112  09:00:00"
    #  - "2026-01-12 09:00:00"
    #  - "20260112"
    if len(s) >= 8 and s[:8].isdigit():
        return s[:8]
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10].replace("-", "")
    # epoch seconds fallback
    try:
        if s.isdigit():
            # If epoch seconds, convert to UTC date (best effort)
            import datetime as _dt
            dt = _dt.datetime.utcfromtimestamp(int(s))
            return dt.strftime("%Y%m%d")
    except:
        pass
    return ""
class App(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self._err: Optional[str] = None
        self._connected = threading.Event()
        self._done = threading.Event()
        self._lock = threading.Lock()
        self._next_id = 1
        self._bars: List[Dict[str, Any]] = []

    
        self._req_err_code: Dict[int,int] = {}
        self._req_err_msg: Dict[int,str] = {}
    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):

            # Fail-fast: HMDS "no data" for this request => mark done
            if int(errorCode) == 162 and int(reqId) > 0:
                with self._lock:
                    self._req_err_code[int(reqId)] = int(errorCode)
                    self._req_err_msg[int(reqId)] = str(errorString)
                self._done.set()
            # print all errors (diagnostic)
            if errorCode != 0:
                print(f"[IBKR][ERR] reqId={reqId} code={errorCode} msg={errorString}")
            # connection-level issues -> fail fast
            if errorCode in (502, 504, 1100, 1101, 1102):
                self._err = f"IBKR connection error {errorCode}: {errorString}"
                self._connected.set()
                self._done.set()

    def nextValidId(self, orderId: int):
        with self._lock:
            self._next_id = max(self._next_id, int(orderId))
        self._connected.set()

    def historicalData(self, reqId, bar):
        with self._lock:
            self._bars.append({
                "time": str(bar.date),
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": float(bar.volume),
            })

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        self._done.set()

def mk_contract_from_resolved(rec: Dict[str, Any]) -> Contract:
    c = Contract()
    c.conId = int(rec["conId"])
    c.secType = rec.get("secType", "STK")
    c.exchange = rec.get("exchange", "SMART")
    pe = rec.get("primaryExchange", "")
    if pe:
        c.primaryExchange = pe
    c.currency = rec.get("currency", "JPY")
    # optional symbol; conId is the identity
    c.symbol = rec.get("symbol", rec.get("input_local", ""))
    return c

def dedupe_sort(bars: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = {}
    for b in bars:
        seen[b["time"]] = b
    return [seen[k] for k in sorted(seen.keys())]

def fetch_one_window(app: App, c: Contract, endDateTime: str) -> List[Dict[str, Any]]:
    with app._lock:
        app._bars = []
        reqId = app._next_id + 1
        app._next_id = reqId
    app._done.clear()

    print(f"[FETCH] conId={c.conId} end={endDateTime} useRTH=1 ...")
    app.reqHistoricalData(
        reqId, c,
        endDateTime=endDateTime,
        durationStr="1 D",
        barSizeSetting="1 min",
        whatToShow="TRADES",
        useRTH=1,
        formatDate=1,
        keepUpToDate=False,
        chartOptions=[]
    )

    ok = app._done.wait(timeout=REQ_TIMEOUT_SEC)
    with app._lock:
        bars = list(app._bars)

    
        err162 = app._req_err_code.get(reqId, 0) == 162
        errMsg = app._req_err_msg.get(reqId, "")
if not ok:
        print(f"[FETCH] TIMEOUT reqId={reqId} conId={c.conId} end={endDateTime} bars_seen={len(bars)}")
        return []
    
    if err162:
        print(f"[FETCH] NO_DATA reqId={reqId} conId={c.conId} end={endDateTime} msg={errMsg}")
        return []
print(f"[FETCH] OK reqId={reqId} conId={c.conId} bars={len(bars)}")
    return bars

def main():
    if len(sys.argv) < 4:
        print("usage: python tools/ibkr_fetch_jp_1m_lunch.py <resolved_json> <YYYY-MM-DD> <out_dir>")
        return 2

    resolved_path, as_of, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out_dir, exist_ok=True)

    recs = json.load(open(resolved_path, "r", encoding="utf-8"))
    if not isinstance(recs, list) or not recs:
        print("Resolved file empty/invalid")
        return 2

    app = App()
    app.connect(HOST, PORT, CLIENT_ID)
    t = threading.Thread(target=app.run, daemon=True)
    t.start()

    if not app._connected.wait(timeout=CONNECT_TIMEOUT_SEC):
        print("[IBKR] CONNECT TIMEOUT: no nextValidId. Is IB Gateway running and API enabled?")
        try: app.disconnect()
        except: pass
        return 2
    if app._err:
        print(app._err)
        try: app.disconnect()
        except: pass
        return 2

    windows = [("11:30", "AM"), ("15:00", "PM")]  # JP RTH windows; lunch gap handled by merging
    any_fail = False

    ymd_compact = as_of.replace("-", "")

    for rec in recs:
        sym_local = rec.get("input_local", rec.get("symbol", "UNK"))
        c = mk_contract_from_resolved(rec)

        allbars: List[Dict[str, Any]] = []
        for hhmm, tag in windows:
            bars = fetch_one_window(app, c, ymd_to_ib_end(as_of, hhmm))
            if not bars:
                any_fail = True
            allbars.extend(bars)

        merged = dedupe_sort(allbars)
        filtered = [b for b in merged if time_to_yyyymmdd(str(b.get("time",""))) == ymd_compact]

        out_path = os.path.join(out_dir, f"{sym_local}_1m_{as_of}.csv")
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("time,open,high,low,close,volume\n")
            for b in filtered:
                f.write(f"{b['time']},{b['open']},{b['high']},{b['low']},{b['close']},{b['volume']}\n")

        print(f"[WROTE] {out_path} rows={len(filtered)} conId={c.conId}")

    try: app.disconnect()
    except: pass

    # NOTE: daemon thread will die when process exits; we return regardless.
    return 2 if any_fail else 0

if __name__ == "__main__":
    raise SystemExit(main())
# __HAT_WRITE_TEST__ 2026-01-11T20:43:12.6915794-08:00
