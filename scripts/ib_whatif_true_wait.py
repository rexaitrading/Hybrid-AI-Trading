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
ib.reqMarketDataType(3)
t = ib.reqMktData(c, "", False, False)
ib.sleep(1.5)
px = t.ask if (t.ask and t.ask > 0) else (t.bid if (t.bid and t.bid > 0) else 150.00)
o = LimitOrder("BUY", 1, round(px, 2), whatIf=True)
o.account = acct
trade = ib.placeOrder(c, o)
for _ in range(20):  # wait up to ~10s
    ib.sleep(0.5)
    logstate = next(
        (e.orderState for e in trade.log if hasattr(e, "orderState") and e.orderState),
        None,
    )
    if logstate:
        print("status:", trade.orderStatus.status)
        print(
            "commission:",
            getattr(logstate, "commission", None),
            getattr(logstate, "commissionCurrency", ""),
        )
        print(
            "init/maint margin:",
            getattr(logstate, "initMarginChange", None),
            getattr(logstate, "maintMarginChange", None),
        )
        break
else:
    print("orderState not populated yet")
ib.disconnect()
