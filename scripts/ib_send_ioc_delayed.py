import math
import os

from ib_insync import *


def v(x):
    try:
        return x is not None and x > 0 and not math.isnan(x)
    except:
        return False


def minTick(ib, c):
    try:
        return float(getattr(ib.reqContractDetails(c)[0], "minTick", 0.01) or 0.01)
    except:
        return 0.01


def clamp(limit, ref, tick_cap, tk, side):
    ref = ref if v(ref) else limit
    move = (limit - ref) if side == "BUY" else (ref - limit)
    maxm = tick_cap * tk
    if move > maxm:
        return round(ref + maxm, 2) if side == "BUY" else round(ref - maxm, 2)
    return limit


def main():
    host = os.getenv("IB_HOST", "127.0.0.1")
    port = int(os.getenv("IB_PORT", "7498"))
    cid = int(os.getenv("IB_CLIENT_ID", "301"))
    sym = os.getenv("SYMBOL", "AAPL").upper()
    side = os.getenv("SIDE", "BUY").upper()
    qty = int(os.getenv("QTY", "1"))
    bps = int(os.getenv("SLIPPAGE_BPS", "5"))
    tick_cap = int(os.getenv("TICK_CAP", "20") or 20)

    ib = IB()
    print(f"[CONNECT] {host}:{port} cid={cid}")
    ib.connect(host, port, clientId=cid)
    try:
        c = Stock(sym, "SMART", "USD")
        ib.qualifyContracts(c)

        # try LIVE first
        try:
            ib.reqMarketDataType(1)
        except:
            pass
        t = ib.reqMktData(c, "", False, False)
        ib.sleep(1.0)
        bid = float(t.bid) if v(t.bid) else None
        ask = float(t.ask) if v(t.ask) else None
        last = float(t.last) if v(t.last) else None

        # fallback to DELAYED if all missing
        if not (v(bid) or v(ask) or v(last)):
            try:
                ib.reqMarketDataType(3)  # DELAYED
            except:
                pass
            t = ib.reqMktData(c, "", False, False)
            ib.sleep(1.0)
            bid = float(t.bid) if v(t.bid) else None
            ask = float(t.ask) if v(t.ask) else None
            last = float(t.last) if v(t.last) else None
            src = "DELAYED"
        else:
            src = "LIVE"

        print(f"[QUOTE/{src}] {sym} bid={bid} ask={ask} last={last}")
        tk = minTick(ib, c)
        eff = bps / 10_000.0

        if side == "BUY":
            base = ask if v(ask) else last
            if not v(base):
                print("[ABORT] no price even after delayed fallback")
                return
            raw = round(base * (1 + eff), 2)
            ref = ask if v(ask) else base
            limit = clamp(raw, ref, tick_cap, tk, side)
        else:
            base = bid if v(bid) else last
            if not v(base):
                print("[ABORT] no price even after delayed fallback")
                return
            raw = round(base * (1 - eff), 2)
            ref = bid if v(bid) else base
            limit = clamp(raw, ref, tick_cap, tk, side)

        notional = round(limit * qty, 2)
        if notional <= 0:
            print("[ABORT] invalid notional")
            return

        o = LimitOrder(
            side,
            qty,
            limit,
            tif=os.getenv("TIF", "IOC"),
            outsideRth=os.getenv("OUTSIDE_RTH", "true").lower() in ("1", "true", "yes"),
        )
        tr = ib.placeOrder(c, o)
        print(f"[PLAN] {side} {qty} {sym} @ ~{limit} (IOC) notionalÃ¢â€°Ë†${notional}")
        print("[SUBMIT] sent, waiting...")
        for _ in range(40):
            ib.sleep(0.2)
            if tr.orderStatus.status in ("Filled", "Cancelled", "Inactive"):
                break
        s = tr.orderStatus
        print(f"[RESULT] status={s.status} filled={s.filled} avgFill={s.avgFillPrice}")
    finally:
        ib.disconnect()
        print("[DONE] disconnected.")


if __name__ == "__main__":
    main()
