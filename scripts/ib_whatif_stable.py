from ib_insync import IB, Stock, LimitOrder
import os, math, time

SENTINEL = 1.79e308  # DBL_MAX

def is_unknown(x):
    return x is None or (isinstance(x, float) and x > 1e300)

ib = IB()
ib.connect(os.getenv("IB_HOST","127.0.0.1"),
           int(os.getenv("IB_PORT","4002")),
           int(os.getenv("IB_CLIENT_ID","901")), timeout=20)

acct = ib.managedAccounts()[0]
c = Stock("AAPL","SMART","USD", primaryExchange="NASDAQ")
ib.qualifyContracts(c)

# choose a sane limit price using delayed data (optional)
ib.reqMarketDataType(3)            # 3 = delayed
t = ib.reqMktData(c, "", False, False); ib.sleep(1.5)
px = (t.ask if (t.ask and t.ask>0) else (t.bid if (t.bid and t.bid>0) else 150.00))
px = round(px, 2)

o = LimitOrder("BUY", 1, px); o.account = acct; o.tif = "DAY"

best = None
for attempt in range(3):           # a couple of passes is enough
    state = ib.whatIfOrder(c, o)
    fields = (
        getattr(state, "initMarginChange", None),
        getattr(state, "maintMarginChange", None),
        getattr(state, "equityWithLoanChange", None),
        getattr(state, "commission", None),
    )
    if not any(is_unknown(v) for v in fields):
        best = state
        break
    ib.sleep(1.0)                  # give the risk engine a moment

if best is None:
    best = state

def g(s, n, d=None): return getattr(s, n, d)
print("account:", acct, "limit:", px)
print("status:", g(best, "status"))
print("warningText:", g(best, "warningText"))
print("commission:", g(best, "commission"), g(best, "commissionCurrency",""))
print("initMarginChange:", g(best, "initMarginChange"))
print("maintMarginChange:", g(best, "maintMarginChange"))
print("equityWithLoanChange:", g(best, "equityWithLoanChange"))

ib.disconnect()