param([string]$Host="127.0.0.1",[int]$Port=4002,[int]$ClientId=1001)

$py="$env:USERPROFILE\OneDrive\文件\HybridAITrading\.venv\Scripts\python.exe"
@"
from ib_insync import *
ib=IB(); ib.connect("$Host",$Port,clientId=$ClientId,timeout=30)
print("CONNECT:", True)
try: print("serverVersion:", ib.client.serverVersion())
except: pass
try: print("currentTime:", ib.reqCurrentTime())
except: pass

# Open orders (all clients)
ib.reqAllOpenOrders(); ib.sleep(1.0)
print("\nOPEN ORDERS:")
seen=set()
for o in ib.orders():
    key=(getattr(o,'permId',0), o.orderId, getattr(o,'goodAfterTime',''), getattr(o,'goodTillDate',''))
    if key in seen: continue
    seen.add(key)
    print(f" permId={getattr(o,'permId',0)} orderId={o.orderId} {o.orderType} qty={o.totalQuantity} "
          f"lmt={getattr(o,'lmtPrice',None)} tif={o.tif} "
          f"GAT={getattr(o,'goodAfterTime',None)} GTD={getattr(o,'goodTillDate',None)}")

print("\nTRADES:")
for t in ib.trades():
    o,c,s = t.order, t.contract, t.orderStatus
    print(f" id={o.orderId} permId={getattr(o,'permId',0)} {getattr(c,'symbol','?')} {o.action} {o.totalQuantity} "
          f"status={s.status} filled={s.filled} whyHeld={s.whyHeld}")

print("\nPOSITIONS:")
for p in ib.positions():
    print(getattr(p.contract,"symbol","?"), p.position, "avgCost", p.avgCost)

print("\nACCOUNT (NLV/AF/BP):")
keep={"NetLiquidation","AvailableFunds","BuyingPower"}
vals = {a.tag:(a.value,a.currency) for a in ib.accountValues() if a.tag in keep}
for k in keep:
    if k in vals: print(k, ":", *vals[k])
ib.disconnect()
"@ | & $py -
