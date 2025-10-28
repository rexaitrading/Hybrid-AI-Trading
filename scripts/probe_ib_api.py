import os

from ib_insync import *

HOST = os.getenv("IB_HOST", "127.0.0.1")
PORT = int(os.getenv("IB_PORT", "4002"))
CID = int(os.getenv("IB_CLIENT_ID", "3021"))


def main():
    ib = IB()
    ok = ib.connect(HOST, PORT, clientId=CID, timeout=25)
    print("Connected:", bool(ok))
    if not ok:
        return 1
    print("Time:", ib.reqCurrentTime())
    print(
        "OpenOrders:",
        [
            (o.order.permId, o.order.action, o.order.totalQuantity, o.orderState.status)
            for o in ib.openOrders()
        ],
    )
    print("Positions:", [(p.contract.symbol, p.position, p.avgCost) for p in ib.positions()])
    ib.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
