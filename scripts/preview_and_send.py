from ib_insync import *
import os, math
from decimal import Decimal, ROUND_HALF_UP

def d2(x): return float(Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
def valid(x):
    try: return x is not None and x>0 and not math.isnan(x)
    except: return False

def tick_size(ib,c):
    try: return float(getattr(ib.reqContractDetails(c)[0], "minTick", 0.01) or 0.01)
    except: return 0.01

def clamp_by_ticks(limit, ref, max_ticks, tk, side):
    ref = ref if valid(ref) else limit
    move = (limit-ref) if side=="BUY" else (ref-limit)
    if move > max_ticks*tk:
        return d2(ref + max_ticks*tk) if side=="BUY" else d2(ref - max_ticks*tk)
    return limit

def main():
    host=os.getenv("IB_HOST","127.0.0.1"); port=int(os.getenv("IB_PORT","7497")); cid=int(os.getenv("IB_CLIENT_ID","201"))
    symbol=os.getenv("SYMBOL","AAPL").upper()
    side=os.getenv("SIDE","BUY").upper()
    qty=int(os.getenv("QTY","1")); bps=int(os.getenv("SLIPPAGE_BPS","5"))
    tif=os.getenv("TIF","IOC"); tick_cap=int(os.getenv("TICK_CAP","20"))
    max_notional=float(os.getenv("MAX_NOTIONAL_USD","100000"))
    abort_no_quote=os.getenv("ABORT_IF_NO_QUOTE","true").lower() in ("1","true","yes")
    outside_rth=os.getenv("OUTSIDE_RTH","true").lower() in ("1","true","yes")

    print(f"[CHECK] SYMBOL={symbol}  SIDE={side}  QTY={qty}  BPS={bps}  TIF={tif}  TICK_CAP={tick_cap}")
    ib=IB(); print(f"[CONNECT] {host}:{port} cid={cid}"); ib.connect(host,port,clientId=cid)
    try:
        c=Stock(symbol,"SMART","USD"); ib.qualifyContracts(c)
        t=ib.reqMktData(c,"",False,False); ib.sleep(1.0)
        bid=float(t.bid) if valid(t.bid) else None
        ask=float(t.ask) if valid(t.ask) else None
        last=float(t.last) if valid(t.last) else None
        tk=tick_size(ib,c)
        print(f"[QUOTE] {symbol}  bid={bid}  ask={ask}  last={last}  tick={tk}")

        if abort_no_quote and not (valid(bid) or valid(ask)):
            print("[ABORT] No live bid/ask (likely after-hours)."); return

        base = (ask if side=="BUY" else bid) if (valid(ask) if side=="BUY" else valid(bid)) else last
        if not valid(base):
            print("[BLOCK] No usable price (bid/ask/last invalid)."); return

        raw = d2(base * (1 + (bps/10_000.0)) if side=="BUY" else base * (1 - (bps/10_000.0)))
        ref = ask if (side=="BUY" and valid(ask)) else (bid if (side=="SELL" and valid(bid)) else base)
        limit = clamp_by_ticks(raw, ref, tick_cap, tk, side)
        notional = d2(limit*qty)

        print(f"[PREVIEW] Will {side} {qty} {symbol}  @ ~{limit}  (TIF={tif}, outsideRth={outside_rth})  notional≈${notional:,.2f}")
        if notional <= 0 or notional > max_notional:
            print(f"[BLOCK] Invalid or exceeds cap (${max_notional:,.2f})."); return

        ans = input("Type YES to send, anything else to cancel: ").strip().upper()
        if ans != "YES":
            print("[CANCELLED] by user."); return

        order = LimitOrder(side, qty, limit, tif=tif, outsideRth=outside_rth)
        tr = ib.placeOrder(c, order)
        print("[SUBMIT] sent, waiting...")
        for _ in range(30):
            ib.sleep(0.2)
            if tr.orderStatus.status in ("Filled","Cancelled","Inactive"): break
        print(f"[RESULT] status={tr.orderStatus.status} filled={tr.orderStatus.filled} avgFill={tr.orderStatus.avgFillPrice}")
    finally:
        ib.disconnect(); print("[DONE] disconnected.")
if __name__=="__main__": main()
