from ib_insync import *
import os
ib = IB(); ib.connect(os.getenv("IB_HOST","127.0.0.1"), int(os.getenv("IB_PORT","7497")), clientId=int(os.getenv("IB_CLIENT_ID","201")))
sym = os.getenv("SYMBOL","MSFT").upper()
n=0
for tr in ib.reqOpenOrders():
    c, o = tr.contract, tr.order
    if getattr(c,"symbol","").upper()==sym and getattr(c,"secType","")=="STK":
        ib.cancelOrder(o); n+=1
print(f"[CANCEL] Sent cancel for {n} open {sym} orders.")
ib.disconnect()
