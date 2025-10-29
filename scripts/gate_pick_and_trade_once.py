import csv
import logging
import math
import os
import time
from datetime import datetime

import yaml
from ib_insync import IB, LimitOrder, MarketOrder, Stock, StopOrder

from hybrid_ai_trading.risk.sentiment_gate import score_headlines_for_symbols

# ---- quiet logs ----
if os.getenv("QUIET_LOGS", "true").lower() in ("1", "true", "yes"):
    logging.getLogger().setLevel(logging.ERROR)
    logging.getLogger("hybrid_ai_trading.risk.sentiment_filter").setLevel(logging.ERROR)


# ---- utils ----
def is_num(x):
    return isinstance(x, (int, float)) and not math.isnan(x) and x > 0


def round2(x):
    return float(f"{x:.2f}")


# ---- env ----
WATCH = os.getenv("WATCH", "AMZN,MSFT,GOOGL").upper().split(",")
HOURS_BACK = int(os.getenv("GATE_HOURS", "12"))
LIMIT = int(os.getenv("GATE_LIMIT", "150"))
SIDE = os.getenv("SIDE", "BUY")
LIVE_FLAG = os.getenv("IB_LIVE", "false").lower() in ("1", "true", "yes")
FALLBACK = os.getenv("IB_FALLBACK_TO_PAPER", "true").lower() in ("1", "true", "yes")
CLIENT_ID = int(os.getenv("IB_CLIENT_ID", "78"))
QTY = int(os.getenv("TRADE_QTY", "1"))
ASK_ADD = float(os.getenv("ASK_ADD", "0.02"))
TP_PCT = float(os.getenv("TP_PCT", "0.012"))
SL_PCT = float(os.getenv("SL_PCT", "0.006"))
TIF = os.getenv("TIF", "DAY")
SKIP_TICKS = os.getenv("SKIP_TICKS", "true").lower() in (
    "1",
    "true",
    "yes",
)  # default: fast

LIVE_PORTS, PAPER_PORTS = [7496, 4001], [7497, 4002]


def try_connect(ib, live=True):
    for p in LIVE_PORTS if live else PAPER_PORTS:
        try:
            ib.connect("127.0.0.1", p, clientId=CLIENT_ID, timeout=10)
            return p
        except Exception:
            pass
    return None


def try_ticks_fast(ib, contract, max_wait=3.0):
    if SKIP_TICKS:
        return None, None, None
    for mdt in (1, 3, 4):  # realtime -> delayed -> delayed-frozen
        try:
            ib.reqMarketDataType(mdt)
        except Exception:
            pass
        ticker = ib.reqMktData(contract, "", False, False)
        start = time.time()
        while time.time() - start < max_wait:
            ask, bid, last, mid, close = (
                ticker.ask,
                ticker.bid,
                ticker.last,
                ticker.midpoint(),
                ticker.close,
            )
            px = next((p for p in (ask, bid, last, mid, close) if is_num(p)), None)
            if is_num(px):
                return (
                    px,
                    {1: "IB-rt", 3: "IB-delayed", 4: "IB-delayed-frozen"}[mdt],
                    ticker,
                )
            ib.sleep(0.2)
        try:
            ib.cancelMktData(contract)
        except Exception:
            pass
    return None, None, None


def try_ib_hist(ib, contract):
    for what in ("TRADES", "MIDPOINT"):
        try:
            bars = ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr="1 D",
                barSizeSetting="1 min",
                whatToShow=what,
                useRTH=False,
                formatDate=1,
            )
            if bars:
                return bars[-1].close
        except Exception:
            pass
    return None


def try_polygon(symbol):
    key = os.getenv("POLYGON_KEY") or os.getenv("POLYGON_API_KEY")
    if not key:
        return None
    import requests

    try:
        r = requests.get(
            f"https://api.polygon.io/v2/last/trade/{symbol}",
            params={"apiKey": key},
            timeout=5,
        )
        if r.ok:
            px = (r.json() or {}).get("results", {}).get("p")
            if is_num(px):
                return float(px)
    except Exception:
        pass
    try:
        r = requests.get(
            f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}",
            params={"apiKey": key},
            timeout=5,
        )
        if r.ok:
            jd = r.json() or {}
            q = (jd.get("ticker") or {}).get("lastQuote") or {}
            ask = q.get("pAsk")
            bid = q.get("pBid")
            if is_num(ask):
                return float(ask)
            if is_num(bid):
                return float(bid)
    except Exception:
        pass
    return None


def logs_contain(trade, code):
    try:
        return any(f"errorCode={code}" in str(le) for le in (trade.log or []))
    except Exception:
        return False


def wait_status(trade, ib, timeout=4.0):
    end = time.time() + timeout
    while time.time() < end:
        st = trade.orderStatus.status if trade.orderStatus else None
        if st in (
            "Submitted",
            "PreSubmitted",
            "PendingSubmit",
            "Cancelled",
            "Filled",
            "ApiCancelled",
        ):
            return st or "unknown"
        ib.sleep(0.2)
    return trade.orderStatus.status if trade.orderStatus else "unknown"


# ---- pick best ALLOW among WATCH ----
with open("config/config.yaml", "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f) or {}
symbols_str = (cfg.get("sweep_symbols") or "AAPL,MSFT,GOOGL,AMZN,TSLA").upper()
res = score_headlines_for_symbols(symbols_str, hours_back=HOURS_BACK, limit=LIMIT, side=SIDE)
cands = []
for s in res.get("stories", []):
    syms = [x.upper() for x in s.get("symbols", [])]
    if s.get("allow") and any(w in syms for w in WATCH):
        cands.append((s.get("score", 0.0), syms[0], s.get("title", ""), s.get("url", "")))
if not cands:
    print("GATE: no ALLOW in watch set -> nothing to do.")
    raise SystemExit(0)
cands.sort(reverse=True, key=lambda x: x[0])
score, symbol, title, url = cands[0]
print(f"GATE PICK: {symbol} (score={score:.2f})")

# ---- connect IB (LIVE first; optional fallback) ----
ib = IB()


# suppress entitlement noise but keep serious errors
def _ib_err_filter(reqId, errorCode, errorString, contract):
    if errorCode in (10089, 300, 2104, 2106, 2158):  # entitlement/no EId
        return
    print(f"IB ERR {errorCode} | {errorString}")


ib.errorEvent += _ib_err_filter

port = try_connect(ib, live=LIVE_FLAG)
if port is None and LIVE_FLAG and FALLBACK:
    print("LIVE refused; trying PAPER fallback")
    port = try_connect(ib, live=False)
if port is None:
    raise RuntimeError("IB API not reachable (LIVE/PAPER).")

live_now = port in (7496, 4001)
contract = Stock(symbol, "SMART", "USD")
ib.qualifyContracts(contract)

# ---- price discovery ----
px, src, ticker = try_ticks_fast(ib, contract, max_wait=3.0)
mode = "LMT" if is_num(px) and src and src.startswith("IB-") else "MKT"
if not is_num(px):
    px = try_ib_hist(ib, contract) or try_polygon(symbol)
    if not is_num(px):
        raise RuntimeError("No price via ticks/hist/polygon.")
    src = "IB-hist/Polygon"
    mode = "MKT"

try:
    if "ticker" in locals() and ticker:
        ib.cancelMktData(contract)
except Exception:
    pass

ref = float(px) + float(ASK_ADD)
lmt = round2(ref)
tp = round2(lmt * (1 + float(TP_PCT)))
sl = round2(lmt * (1 - float(SL_PCT)))

# ---- place parent then children ----
parent = LimitOrder("BUY", QTY, lmt, tif=TIF) if mode == "LMT" else MarketOrder("BUY", QTY, tif=TIF)
parent.transmit = False
tradeParent = ib.placeOrder(contract, parent)
pstat = wait_status(tradeParent, ib, timeout=4.0)
if mode == "LMT" and pstat == "Cancelled" and logs_contain(tradeParent, 163):
    parent2 = MarketOrder("BUY", QTY, tif=TIF)
    parent2.transmit = False
    tradeParent = ib.placeOrder(contract, parent2)
    pstat = wait_status(tradeParent, ib, timeout=4.0)
    mode = "MKT"
if pstat not in ("Submitted", "PreSubmitted", "PendingSubmit", "Filled"):
    for le in tradeParent.log or []:
        print("LOG:", le)
    raise RuntimeError(f"Parent not accepted (status={pstat}).")

poid = tradeParent.order.orderId
tpChild = LimitOrder("SELL", QTY, tp, tif=TIF)
tpChild.parentId = poid
tpChild.transmit = False
slChild = StopOrder("SELL", QTY, sl, tif=TIF)
slChild.parentId = poid
slChild.transmit = True
ib.placeOrder(contract, tpChild)
ib.placeOrder(contract, slChild)

print(f"SESSION: {'LIVE' if live_now else 'PAPER'} on port {port}")
print(f"PRICE_SRC: {src}  MODE: {mode}")
print(
    f"PLACED: {symbol} x{QTY} @ {('MKT' if mode=='MKT' else lmt)} | TP {tp} | SL {sl} | parentId={poid}"
)

# ---- CSV log ----
logf = f"logs/trades_{datetime.now():%Y%m%d}.csv"
exists = os.path.exists(logf)
with open(logf, "a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    if not exists:
        w.writerow(
            [
                "ts",
                "session",
                "symbol",
                "score",
                "mode",
                "qty",
                "lmt",
                "tp",
                "sl",
                "parentId",
                "title",
                "url",
            ]
        )
    w.writerow(
        [
            datetime.now().isoformat(timespec="seconds"),
            "LIVE" if live_now else "PAPER",
            symbol,
            f"{score:.4f}",
            mode,
            QTY,
            (lmt if mode != "MKT" else "MKT"),
            tp,
            sl,
            poid,
            title,
            url,
        ]
    )
ib.disconnect()
