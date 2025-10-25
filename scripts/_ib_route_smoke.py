from ib_insync import *
import time, sys

sym, side, qty, off, host, port, cid, ussl, secs = sys.argv[1:]
qty=int(qty); off=float(off); port=int(port); cid=int(cid); ussl=int(ussl); secs=int(secs)

ib = IB()
ib.client.setConnectOptions(f"UseSSL={ussl}")
assert ib.connect(host, port, clientId=cid, timeout=15), "connect failed"

ib.reqMarketDataType(3)
c = Stock(sym, "SMART", "USD")
ib.qualifyContracts(c)
t = ib.reqMktData(c, "", False, False)
ib.sleep(1.5)

bid = t.bid or t.close or t.last
ask = t.ask or t.close or t.last
if not (bid and ask):
    print("no quotes; abort"); ib.disconnect(); sys.exit(0)

if side == "BUY":
    px = round(max(0.01, min(ask, max(bid, 0)) - off/100.0), 2)
else:
    px = round(max(0.01, max(bid, 0) + off/100.0), 2)

o = LimitOrder(side, qty, px)
tr = ib.placeOrder(c, o)
print("placed", tr.orderStatus.status, side, qty, sym, "at", px)

deadline = time.time() + secs
while time.time() < deadline and tr.orderStatus.status in ("PendingSubmit","PendingCancel","PreSubmitted","Submitted"):
    ib.sleep(0.25)

print("status_before_cancel:", tr.orderStatus.status)
ib.cancelOrder(o)
ib.sleep(1.0)
print("status_after_cancel:", tr.orderStatus.status)
ib.disconnect()
