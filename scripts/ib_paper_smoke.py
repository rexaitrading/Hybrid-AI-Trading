import asyncio
import os
import time

from ib_insync import IB, LimitOrder, Stock

IB_HOST = os.getenv("IB_HOST", "127.0.0.1")
IB_PORT = int(os.getenv("IB_PORT", "7497"))  # TWS paper default; GW paper often 4002
IB_CLIENT = int(os.getenv("IB_CLIENT_ID", "3021"))
SYMBOL = os.getenv("SMOKE_SYMBOL", "AAPL")
QTY = int(os.getenv("SMOKE_QTY", "1"))
LMT = float(os.getenv("SMOKE_LMT", "1.00"))  # intentionally safe far price for paper


def main():
    ib = IB()
    print(f"Connecting {IB_HOST}:{IB_PORT} clientId={IB_CLIENT} ...")
    ib.connect(IB_HOST, IB_PORT, clientId=IB_CLIENT, timeout=10)
    a = Stock(SYMBOL, "SMART", "USD")

    print("Qualifying contract...")
    ib.qualifyContracts(a)

    o = LimitOrder("BUY", QTY, LMT)
    print(f"Placing BUY {QTY} {SYMBOL} @ {LMT} (paper)")
    trade = ib.placeOrder(a, o)

    # Let it reach a known state
    ib.sleep(2.0)
    status = trade.orderStatus.status if trade.orderStatus else None
    print("Status after 2s:", status)

    # Cancel and confirm cancellation
    ib.cancelOrder(o)
    ib.sleep(1.0)
    status = trade.orderStatus.status if trade.orderStatus else None
    print("Final status:", status)

    ib.disconnect()


if __name__ == "__main__":
    main()
