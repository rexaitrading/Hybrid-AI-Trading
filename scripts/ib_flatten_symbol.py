from ib_insync import IB, Stock, LimitOrder
import os
from decimal import Decimal, ROUND_HALF_UP

def dround(x, places=2): return float(Decimal(x).quantize(Decimal(10)**-places, rounding=ROUND_HALF_UP))
def q(ib,c):
    t=ib.reqMktData(c,"",False,False); ib.sleep(1.0)
    return (float(t.bid) if t.bid else None, float(t.ask) if t.ask else None, float(t.last) if t.last else None)
def tick_size(ib,c):
    try: return float(getattr(ib.reqContractDetails(c)[0], "minTick", 0.01) or 0.01)
    except Exception: return 0.01
def clamp(limit,ref,max_ticks,tick,side):
    move = limit - ref if side=="BUY" else ref - limit
    max_move = max_ticks*tick
    if move>max_move: return ref+max_move if side=="BUY" else ref-max_move
    return limit

def main():
    host=os.getenv("IB_HOST","127.0.0.1"); port=int(os.getenv("IB_PORT","7497")); cid=int(os.getenv("IB_CLIENT_ID","201"))
    symbol=os.getenv("SYMBOL","AAPL").upper(); slip=int(os.getenv("SLIPPAGE_BPS","5")); tick_cap=int(os.getenv("TICK_CAP","20"))
    ib=IB(); print(f"[CONNECT] {host}:{port} clientId={cid}"); ib.connect(host,port,clientId=cid)
    try:
        pos=0; c=None
        for p in ib.positions():
            if getattr(p.contract,"symbol","")==symbol and getattr(p.contract,"secType","")=="STK":
                pos=int(p.position); c=p.contract; break
        if pos==0: print(f"[FLATTEN] No position in {symbol}."); return
        if c is None: c=Stock(symbol,"SMART","USD"); ib.qualifyContracts(c)
        bid,ask,last=q(ib,c); tk=tick_size(ib,c)
        side="SELL" if pos>0 else "BUY"; qty=abs(pos)
        bps=slip/10_000.0
        if side=="BUY":
            base=ask or last; assert base is not None, "No ask/last"
            raw=dround(base*(1+bps),2); limit=dround(clamp(raw, ask, tick_cap, tk, side),2)
        else:
            base=bid or last; assert base is not None, "No bid/last"
            raw=dround(base*(1-bps),2); limit=dround(clamp(raw, bid, tick_cap, tk, side),2)
        print(f"[PLAN] {side} {qty} {symbol} @ ~{limit} (IOC) to FLAT")
        tr=ib.placeOrder(c, LimitOrder(side, qty, limit, tif="IOC", outsideRth=True))
        print("[SUBMIT] sent, waiting...")
        for _ in range(30):
            ib.sleep(0.2)
            if tr.orderStatus.status in ("Filled","Cancelled","Inactive"): break
        print(f"[RESULT] status={tr.orderStatus.status} filled={tr.orderStatus.filled} avgFill={tr.orderStatus.avgFillPrice}")
    finally:
        ib.disconnect(); print("[DONE] disconnected.")
if __name__=="__main__": main()
