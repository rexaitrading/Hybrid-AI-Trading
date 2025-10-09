from ib_insync import IB, Stock, LimitOrder
import os, math
def valid(x):
    try: return x is not None and x>0 and not math.isnan(x)
    except: return False
def q(ib,c):
    t=ib.reqMktData(c,"",False,False); ib.sleep(0.8)
    bid=t.bid if valid(t.bid) else None
    ask=t.ask if valid(t.ask) else None
    last=t.last if valid(t.last) else None
    return bid,ask,last
ib=IB(); ib.connect(os.getenv("IB_HOST","127.0.0.1"), int(os.getenv("IB_PORT","7497")), clientId=int(os.getenv("IB_CLIENT_ID","201")))
slip_bps = int(os.getenv("SLIPPAGE_BPS","5"))
sent=0
for p in ib.positions():
    c=p.contract
    if getattr(c,"secType","")!="STK": continue
    qty=int(p.position)
    if qty==0: continue
    side="SELL" if qty>0 else "BUY"
    bid,ask,last = q(ib,c)
    base = (ask if side=="BUY" else bid) or last
    if not valid(base): continue
    bps=slip_bps/10_000.0
    limit = round(base*(1+bps),2) if side=="BUY" else round(base*(1-bps),2)
    ib.placeOrder(c, LimitOrder(side, abs(qty), limit, tif="IOC", outsideRth=True)); sent+=1
print(f"[PANIC] Flatten sent for {sent} positions."); ib.disconnect()
