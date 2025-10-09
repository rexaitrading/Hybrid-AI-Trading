from ib_insync import *
import os, pathlib

def main():
    host = os.getenv("IB_HOST","127.0.0.1")
    port = int(os.getenv("IB_PORT","7497") or 7497)
    cid  = int(os.getenv("IB_CLIENT_ID","201") or 201)

    ib = IB()
    ib.connect(host, port, clientId=cid)

    # positions
    positions = [(p.contract.symbol, int(p.position)) for p in ib.positions()]

    # open orders
    opens = []
    for t in ib.reqOpenOrders():
        c, o, s = t.contract, t.order, t.orderStatus
        opens.append((getattr(c,"symbol","?"), o.action, int(o.totalQuantity), s.status))

    ib.disconnect()

    print("[STATUS] Positions:", positions or "[]")
    print("[STATUS] Open orders:", opens or "[]")

    # last 10 order log rows
    p = pathlib.Path("logs") / "orders.csv"
    if p.exists():
        print("[STATUS] Last 10 orders.csv:")
        lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in lines[-10:]:
            print(line)
    else:
        print("[STATUS] No logs/orders.csv yet.")

if __name__ == "__main__":
    main()
