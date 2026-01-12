import os, sys, time, json, threading
from typing import Optional, List, Dict, Any

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

HOST = os.environ.get("IB_GATEWAY_HOST", "127.0.0.1")
PORT = int(os.environ.get("IB_GATEWAY_PORT", "4002"))
CLIENT_ID = int(os.environ.get("IB_CLIENT_ID", "77"))

class App(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self._err: Optional[str] = None
        self._details: List[Dict[str, Any]] = []
        self._req_done = threading.Event()
        self._connected_evt = threading.Event()
        self._lock = threading.Lock()
        self._next_id = 1

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        # Connection / session errors
        if errorCode in (502, 504, 1100, 1101, 1102):
            self._err = f"IBKR connection error {errorCode}: {errorString}"
            self._connected_evt.set()
            self._req_done.set()

    def nextValidId(self, orderId: int):
        with self._lock:
            self._next_id = max(self._next_id, int(orderId))
        self._connected_evt.set()

    def contractDetails(self, reqId, contractDetails):
        c = contractDetails.contract
        d = {
            "conId": int(getattr(c, "conId", 0)),
            "symbol": getattr(c, "symbol", ""),
            "secType": getattr(c, "secType", ""),
            "exchange": getattr(c, "exchange", ""),
            "primaryExchange": getattr(c, "primaryExchange", ""),
            "currency": getattr(c, "currency", ""),
            "localSymbol": getattr(c, "localSymbol", ""),
            "tradingClass": getattr(c, "tradingClass", ""),
            "longName": getattr(contractDetails, "longName", ""),
            "minTick": float(getattr(contractDetails, "minTick", 0.0)),
            "timeZoneId": getattr(contractDetails, "timeZoneId", "")
        }
        with self._lock:
            self._details.append(d)

    def contractDetailsEnd(self, reqId: int):
        self._req_done.set()

def mk_contract(symbol: str, secType: str, currency: str, exchange: str, primary: str) -> Contract:
    c = Contract()
    c.symbol = symbol
    c.secType = secType
    c.currency = currency
    c.exchange = exchange
    if primary:
        c.primaryExchange = primary
    return c

def load_cfg(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def pick_best(details: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    best = None
    for d in details:
        if d.get("conId", 0) <= 0:
            continue
        if not best:
            best = d
            continue
        score = int(bool(d.get("primaryExchange"))) + int(bool(d.get("localSymbol")))
        bscore = int(bool(best.get("primaryExchange"))) + int(bool(best.get("localSymbol")))
        if score > bscore:
            best = d
    return best

def resolve_one(app: App, sym: str, secType: str, currency: str, exch: str, primary: str, timeout_sec: float=6.0) -> Optional[Dict[str, Any]]:
    with app._lock:
        app._details = []
    app._req_done.clear()

    with app._lock:
        reqId = app._next_id + 1
        app._next_id = reqId

    c = mk_contract(sym, secType, currency, exch, primary)
    app.reqContractDetails(reqId, c)

    ok = app._req_done.wait(timeout=timeout_sec)
    with app._lock:
        details = list(app._details)

    if not ok:
        return None
    return pick_best(details)

def main():
    if len(sys.argv) < 2:
        print("usage: python tools/ibkr_resolve_contract.py <configs/symbols/JP.json>")
        return 2

    cfg = load_cfg(sys.argv[1])
    currency = cfg.get("currency", "JPY")
    cand = cfg.get("ibkr_resolution_candidates", {})
    exchanges = cand.get("exchanges", ["SMART"])
    primaries = cand.get("primaryExchanges", [""])
    formats = cand.get("symbol_formats", ["{local}"])
    symbols = cfg.get("symbols", [])
    if not symbols:
        print("No symbols in config")
        return 2

    app = App()
    app.connect(HOST, PORT, CLIENT_ID)

    # Start IBKR network loop on background thread (required)
    t = threading.Thread(target=app.run, daemon=True)
    t.start()

    # Wait for nextValidId / connection ready (or error)
    if not app._connected_evt.wait(timeout=4.0):
        print("IBKR connect timeout (no nextValidId). Check IB_GATEWAY_HOST/PORT/CLIENT_ID and IB Gateway running.")
        try: app.disconnect()
        except: pass
        return 2
    if app._err:
        print(app._err)
        try: app.disconnect()
        except: pass
        return 2

    out: List[Dict[str, Any]] = []
    for s in symbols:
        local = str(s.get("local", "")).strip()
        secType = str(s.get("secType", "STK")).strip()
        name = str(s.get("name", "")).strip()

        found = None
        tried = 0
        for fmt in formats:
            sym = fmt.replace("{local}", local)
            for exch in exchanges:
                for primary in primaries:
                    tried += 1
                    found = resolve_one(app, sym, secType, currency, exch, primary, timeout_sec=6.0)
                    if found:
                        found["input_local"] = local
                        found["input_name"] = name
                        found["input_symbol"] = sym
                        found["tried"] = tried
                        out.append(found)
                        break
                if found: break
            if found: break

        if not found:
            out.append({
                "input_local": local,
                "input_name": name,
                "input_symbol": local,
                "error": "NO_MATCH",
                "currency": currency
            })

    try: app.disconnect()
    except: pass

    print(json.dumps(out, indent=2, ensure_ascii=False))
    if any(x.get("error") == "NO_MATCH" for x in out):
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
