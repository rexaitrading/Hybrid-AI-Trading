import math
import os
import time

from ib_insync import IB, LimitOrder, MarketOrder, Stock, StopOrder

# ---------- SETTINGS ----------
SYMBOL = os.getenv("TRADE_SYMBOL", "AMZN")
QTY = int(os.getenv("TRADE_QTY", "1"))
ASK_ADD = float(os.getenv("ASK_ADD", "0.02"))  # LMT @ (ref + ASK_ADD)
TP_PCT = float(os.getenv("TP_PCT", "0.012"))  # +1.20%
SL_PCT = float(os.getenv("SL_PCT", "0.006"))  # -0.60%
LIVE = os.getenv("IB_LIVE", "false").lower() in ("1", "true", "yes")
CLIENT_ID = int(os.getenv("IB_CLIENT_ID", "77"))
TIF = os.getenv("TIF", "DAY")

host, port = "127.0.0.1", (7496 if LIVE else 7497)


def is_num(x):
    return isinstance(x, (int, float)) and not math.isnan(x) and x > 0


def round2(x):
    return float(f"{x:.2f}")


def try_ticks(ib, contract, max_wait=6.0):
    "Try realtime → delayed → delayed-frozen, return (px, source, ticker)"
    for mdt in (1, 3, 4):
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
                src = {1: "IB-rt", 3: "IB-delayed", 4: "IB-delayed-frozen"}[mdt]
                return px, src, ticker
            ib.sleep(0.25)
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


def wait_status(trade, ib, timeout=5.0):
    "Wait for an acceptance/cancel transition."
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


def logs_contain(trade, code):
    try:
        for le in trade.log or []:
            if f"errorCode={code}" in str(le):
                return True
    except Exception:
        pass
    return False


def main():
    ib = IB()
    ib.connect(host, port, clientId=CLIENT_ID)
    contract = Stock(SYMBOL, "SMART", "USD")
    ib.qualifyContracts(contract)

    px, src, ticker = try_ticks(ib, contract, max_wait=6.0)
    mode = "LMT" if is_num(px) and src and src.startswith("IB-") else "MKT"

    if not is_num(px):
        px = try_ib_hist(ib, contract) or try_polygon(SYMBOL)
        if not is_num(px):
            raise RuntimeError(
                f"No price for {SYMBOL} via ticks, IB-hist, or Polygon. Enable delayed data or set POLYGON_KEY."
            )
        src = "IB-hist/Polygon"
        mode = "MKT"  # avoid price-band issues when no live NBBO

    try:
        ib.cancelMktData(contract)
    except Exception:
        pass

    ref = px + ASK_ADD
    lmt = round2(ref)
    tp = round2(lmt * (1 + TP_PCT))
    sl = round2(lmt * (1 - SL_PCT))

    # Parent first: LMT if ticks, else MARKET
    parent = (
        LimitOrder("BUY", QTY, lmt, tif=TIF) if mode == "LMT" else MarketOrder("BUY", QTY, tif=TIF)
    )
    parent.transmit = False

    tradeParent = ib.placeOrder(contract, parent)
    pstat = wait_status(tradeParent, ib, timeout=5.0)

    # If we tried LMT and got 163 band cancel, retry as MKT
    if mode == "LMT" and pstat == "Cancelled" and logs_contain(tradeParent, 163):
        parent2 = MarketOrder("BUY", QTY, tif=TIF)
        parent2.transmit = False
        tradeParent = ib.placeOrder(contract, parent2)
        pstat = wait_status(tradeParent, ib, timeout=5.0)
        mode = "MKT"

    if pstat not in ("Submitted", "PreSubmitted", "PendingSubmit", "Filled"):
        # dump trade log to help debugging
        for le in tradeParent.log or []:
            print("LOG:", le)
        raise RuntimeError(
            f"Parent not accepted (status={pstat}). Aborting children to avoid orphans."
        )

    poid = tradeParent.order.orderId

    # Children after parent accepted; last transmits
    tpChild = LimitOrder("SELL", QTY, tp, tif=TIF)
    tpChild.parentId = poid
    tpChild.transmit = False
    slChild = StopOrder("SELL", QTY, sl, tif=TIF)
    slChild.parentId = poid
    slChild.transmit = True
    tradeTP = ib.placeOrder(contract, tpChild)
    tradeSL = ib.placeOrder(contract, slChild)

    print(f"PRICE_SRC: {src}  MODE: {mode}")
    print(
        f"PLACED: {SYMBOL} x{QTY} @ {('MKT' if mode=='MKT' else lmt)} | TP {tp} | SL {sl} | {'LIVE' if LIVE else 'PAPER'} | parentId={poid}"
    )

    ib.sleep(1.0)
    for t in (tradeParent, tradeTP, tradeSL):
        st = t.orderStatus.status if t.orderStatus else "unknown"
        ot = getattr(t.order, "orderType", "?")
        print(f"{t.order.action} {ot} id={t.order.orderId} -> {st}")

    ib.disconnect()


if __name__ == "__main__":
    main()
