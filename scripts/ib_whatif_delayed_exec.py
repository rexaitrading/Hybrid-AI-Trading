import math
import os

from ib_insync import IB, LimitOrder, Stock

ib = IB()
ib.connect(
    os.getenv("IB_HOST", "127.0.0.1"),
    int(os.getenv("IB_PORT", "4002")),
    int(os.getenv("IB_CLIENT_ID", "901")),
    timeout=20,
)

acct = ib.managedAccounts()[0]
c = Stock("AAPL", "SMART", "USD", primaryExchange="NASDAQ")
ib.qualifyContracts(c)

# Use delayed data if real-time not entitled
ib.reqMarketDataType(3)  # 1=real-time, 3=delayed
t = ib.reqMktData(c, "", False, False)
ib.sleep(2.0)  # let ticks arrive

# Pick a sane executable price
bid = t.bid if (t.bid is not None and t.bid > 0) else math.nan
ask = t.ask if (t.ask is not None and t.ask > 0) else math.nan
mid = (bid + ask) / 2 if (bid == bid and ask == ask) else None  # NaN-safe

px = None
if ask == ask:  # have ask -> buy near ask
    px = round(ask, 2)
elif mid is not None:  # fallback mid
    px = round(mid, 2)
else:
    px = 150.00  # last fallback (should still preview)

o = LimitOrder("BUY", 1, px)
o.account = acct
o.tif = "DAY"

state = ib.whatIfOrder(c, o)


def g(x, n, d=None):
    return getattr(x, n, d)


print("account:", acct, "priceUsed:", px)
print("whatIf.status:", g(state, "status"))
print("warningText:", g(state, "warningText"))
print("commission:", g(state, "commission"), g(state, "commissionCurrency", ""))
print(
    "minCommission/maxCommission:", g(state, "minCommission"), g(state, "maxCommission")
)
print("equityWithLoanChange:", g(state, "equityWithLoanChange"))
print("initMarginChange:", g(state, "initMarginChange"))
print("maintMarginChange:", g(state, "maintMarginChange"))
ib.disconnect()
