import os

from ib_insync import IB, LimitOrder, Stock

SENTINEL = 1.79e308


def bad(v):
    return (v is None) or (isinstance(v, float) and v > 1e300)


ib = IB()
ib.connect(
    os.getenv("IB_HOST", "127.0.0.1"),
    int(os.getenv("IB_PORT", "4002")),
    int(os.getenv("IB_CLIENT_ID", "901")),
    timeout=30,
)

acct = ib.managedAccounts()[0]
c = Stock("AAPL", "SMART", "USD", primaryExchange="NASDAQ")
ib.qualifyContracts(c)

ib.reqMarketDataType(3)
t = ib.reqMktData(c, "", False, False)
ib.sleep(1.5)
px = t.ask if (t.ask and t.ask > 0) else (t.bid if (t.bid and t.bid > 0) else 150.00)
o = LimitOrder("BUY", 1, round(px, 2))
o.account = acct
o.tif = "DAY"

best = None
for _ in range(4):
    st = ib.whatIfOrder(c, o)
    vals = (
        getattr(st, "initMarginChange", None),
        getattr(st, "maintMarginChange", None),
        getattr(st, "equityWithLoanChange", None),
        getattr(st, "commission", None),
    )
    if not any(bad(v) for v in vals):
        best = st
        break
    ib.waitOnUpdate(timeout=1.0)  # keep socket alive and process events

if best is None:
    best = st


def g(x, n, d=None):
    return getattr(x, n, d)


print("account:", acct, "limit:", o.lmtPrice)
print("status:", g(best, "status"))
print("commission:", g(best, "commission"), g(best, "commissionCurrency", ""))
print("initMarginChange:", g(best, "initMarginChange"))
print("maintMarginChange:", g(best, "maintMarginChange"))
print("equityWithLoanChange:", g(best, "equityWithLoanChange"))

ib.disconnect()
