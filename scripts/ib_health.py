from ib_insync import *
import time

HOST="127.0.0.1"; PORT=4002; CID=3021; TIMEOUT=30

def snapshot_values(ib: IB, acct: str):
    # version-proof: low-level subscribe to populate accountValues
    ib.client.reqAccountUpdates(True, acct)
    t0 = time.time()
    while time.time() - t0 < 3:
        ib.waitOnUpdate(timeout=1.0)
    vals = ib.accountValues() or []
    ib.client.reqAccountUpdates(False, acct)
    want = {"NetLiquidation","TotalCashValue","BuyingPower","AvailableFunds"}
    return [(v.tag, v.value, v.currency) for v in vals if v.tag in want]

def main():
    ib = IB(); ib.connect(HOST, PORT, clientId=CID, timeout=TIMEOUT)
    print("connected:", ib.isConnected(), "serverTime:", ib.reqCurrentTime())
    acct = (ib.managedAccounts() or [""])[0]
    print("account:", acct)
    print("summary:", snapshot_values(ib, acct))
    print("openTrades:", [(t.order.orderId, t.orderStatus.status) for t in ib.openTrades()])
    ib.disconnect()

if __name__ == "__main__":
    main()
