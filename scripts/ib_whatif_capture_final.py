import os

from ib_insync import IB, LimitOrder, Stock


def is_unknown(v):
    return v is None or (isinstance(v, float) and v > 1e300)  # DBL_MAX sentinel


def good(state):
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
c = Stock("AAPL", "SMART", "USD", primaryExchange="NASDAQ")
ib.qualifyContracts(c)

# Use delayed market data to anchor price
ib.reqMarketDataType(3)
t = ib.reqMktData(c, "", False, False)
ib.sleep(1.5)
base_px = (
    t.ask if (t.ask and t.ask > 0) else (t.bid if (t.bid and t.bid > 0) else 150.00)
)
base_px = round(base_px, 2)

best = None
for attempt in range(8):  # ~8 attempts over ~16â€“20s
    px = round(base_px + (attempt * 0.01), 2)  # tiny nudge to avoid caching
    o = LimitOrder("BUY", 1, px)
    o.account = acct
    o.tif = "DAY"

    st = ib.whatIfOrder(c, o)  # request preview
    if good(st):
        best = st
        print(f"[pass {attempt+1}] got FINAL at {px}")
        break
    else:
        # keep the socket alive and let Gateway finish computing
        print(f"[pass {attempt+1}] placeholder at {px}; waiting â€¦")
        ib.waitOnUpdate(timeout=1.5)

# final grace + one last fetch
if best is None:
    ib.waitOnUpdate(timeout=2.0)
    o = LimitOrder("BUY", 1, base_px)
    o.account = acct
    o.tif = "DAY"
    st = ib.whatIfOrder(c, o)
    if good(st):
        best = st

print("account:", acct, "base_limit:", base_px)
if best:
    print("status:", getattr(best, "status", None))
    print(
        "commission:",
        getattr(best, "commission", None),
        getattr(best, "commissionCurrency", ""),
    )
    print("initMarginChange:", getattr(best, "initMarginChange", None))
    print("maintMarginChange:", getattr(best, "maintMarginChange", None))
    print("equityWithLoanChange:", getattr(best, "equityWithLoanChange", None))
else:
    print("Still seeing placeholder margins after retries.")

# hold the socket a touch longer so late packets don't arrive post-disconnect
ib.waitOnUpdate(timeout=1.0)
ib.disconnect()
