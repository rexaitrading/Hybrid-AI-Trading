import os

from ib_insync import IB, LimitOrder, Stock

SENTINEL = 1.79e308


def is_unknown(v):
    return v is None or (isinstance(v, float) and v > 1e300)


def good_enough(state):
    # Accept as soon as *margins* are non-sentinel (commission may still be sentinel on some routes)
    return (
        state
        and not is_unknown(getattr(state, "initMarginChange", None))
        and not is_unknown(getattr(state, "maintMarginChange", None))
    )


ib = IB()
ib.connect(
    os.getenv("IB_HOST", "127.0.0.1"),
    int(os.getenv("IB_PORT", "4002")),
    int(os.getenv("IB_CLIENT_ID", "901")),
    timeout=30,
)

acct = ib.managedAccounts()[0]

# Contract
c = Stock("AAPL", "SMART", "USD", primaryExchange="NASDAQ")
ib.qualifyContracts(c)

# Price anchor (delayed ok)
ib.reqMarketDataType(3)
t = ib.reqMktData(c, "", False, False)
ib.sleep(1.5)
px = t.ask if (t.ask and t.ask > 0) else (t.bid if (t.bid and t.bid > 0) else 150.00)
px = round(px, 2)

# Build order
o = LimitOrder("BUY", 1, px)
o.account = acct
o.tif = "DAY"

best = None
for attempt in range(8):  # ~8s total with sleeps; gateway shows final within <1s
    state = ib.whatIfOrder(c, o)
    if good_enough(state):
        best = state
        break
    # keep socket alive & let gateway compute final
    ib.waitOnUpdate(timeout=1.0)

if best is None:
    # Last chance â€“ one more settle and final try
    ib.waitOnUpdate(timeout=1.0)
    best = ib.whatIfOrder(c, o)


def g(x, n, d=None):
    return getattr(x, n, d)


print("account:", acct, "limit:", px)
print("status:", g(best, "status") if best else None)
print(
    "commission:",
    g(best, "commission", None),
    g(best, "commissionCurrency", "") if best else "",
)
print("initMarginChange:", g(best, "initMarginChange", None))
print("maintMarginChange:", g(best, "maintMarginChange", None))
print("equityWithLoanChange:", g(best, "equityWithLoanChange", None))

ib.disconnect()
