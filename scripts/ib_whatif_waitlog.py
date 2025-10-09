from ib_insync import IB, Stock, LimitOrder
import os, time, math

ib = IB()
ib.connect(os.getenv("IB_HOST","127.0.0.1"),
           int(os.getenv("IB_PORT","4002")),
           int(os.getenv("IB_CLIENT_ID","901")), timeout=30)

acct = ib.managedAccounts()[0]
c = Stock("AAPL","SMART","USD", primaryExchange="NASDAQ")
ib.qualifyContracts(c)

# Use delayed data just to pick a sane price
ib.reqMarketDataType(3)
t = ib.reqMktData(c, "", False, False); ib.sleep(1.5)
px = t.ask if (t.ask and t.ask > 0) else (t.bid if (t.bid and t.bid > 0) else 150.00)
px = round(px, 2)

o = LimitOrder("BUY", 1, px, whatIf=True)
o.account = acct
o.tif = "DAY"

trade = ib.placeOrder(c, o)

order_state = None
for _ in range(40):                  # ~20s max
    ib.waitOnUpdate(timeout=0.5)     # let IB events process
    # OrderState shows up in trade.log entries
    for e in trade.log:
        if hasattr(e, "orderState") and e.orderState:
            order_state = e.orderState
            break
    if order_state:
        break

def g(x, n, d=None): return getattr(x, n, d)

print("account:", acct, "limit:", px)
print("status:", trade.orderStatus.status)
if order_state:
    print("commission:", g(order_state, "commission"), g(order_state, "commissionCurrency",""))
    print("initMarginChange:", g(order_state, "initMarginChange"))
    print("maintMarginChange:", g(order_state, "maintMarginChange"))
    print("equityWithLoanChange:", g(order_state, "equityWithLoanChange"))
else:
    print("orderState still not populated (keep alive longer)")

ib.disconnect()