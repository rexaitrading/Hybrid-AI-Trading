import os

from ib_insync import IB, LimitOrder, Stock

ib = IB()
ib.connect(
    os.getenv("IB_HOST", "127.0.0.1"),
    int(os.getenv("IB_PORT", "4002")),
    int(os.getenv("IB_CLIENT_ID", "901")),
    timeout=15,
)

c = Stock("AAPL", "SMART", "USD")
ib.qualifyContracts(c)

t = ib.placeOrder(c, LimitOrder("BUY", 1, 100.00, whatIf=True))
ib.sleep(1.0)

state = next(
    (e.orderState for e in t.log if hasattr(e, "orderState") and e.orderState), None
)
print("whatIfStatus:", t.orderStatus.status)
if state:
    print(
        "commission:",
        getattr(state, "commission", None),
        getattr(state, "commissionCurrency", ""),
    )
    print(
        "min/max commission:",
        getattr(state, "minCommission", None),
        getattr(state, "maxCommission", None),
    )
else:
    print("orderState not available in trade.log yet")
ib.disconnect()
