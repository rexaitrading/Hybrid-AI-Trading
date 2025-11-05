import os

from ib_insync import *

HOST = os.getenv("IB_HOST", "127.0.0.1")
PORT = int(os.getenv("IB_PORT", "4002"))
CID = int(os.getenv("IB_CLIENT_ID", "3021"))
ib = IB()
ib.connect(HOST, PORT, clientId=CID, timeout=25)
aapl = Stock("AAPL", "SMART", "USD")
trade = ib.placeOrder(aapl, LimitOrder("BUY", 1, 0.01))  # far from market; wonâ€™t fill
ib.sleep(3)
print(
    "Status:",
    trade.orderStatus.status,
    "Filled:",
    trade.orderStatus.filled,
    "AvgFillPrice:",
    trade.orderStatus.avgFillPrice,
)
if trade.orderStatus.status not in ("Filled", "ApiCancelled", "Cancelled"):
    ib.cancelOrder(trade.order)
    ib.sleep(2)
    print("After cancel ->", trade.orderStatus.status)
ib.disconnect()
