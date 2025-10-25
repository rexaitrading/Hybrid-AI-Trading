from ib_insync import *
import time

def main():
    ib = IB()
    ib.client.setConnectOptions("UseSSL=0")  # 4002 plain socket
    assert ib.connect("127.0.0.1", 4002, clientId=940, timeout=15), "connect failed"

    ib.reqMarketDataType(3)  # delayed if real-time not allowed on paper
    aapl = Stock("AAPL","SMART","USD")
    ib.qualifyContracts(aapl)
    t = ib.reqMktData(aapl, "", False, False)
    ib.sleep(1.5)

    # Build a reasonable buy limit near the market
    bids = [x for x in (t.bid, t.close, t.last) if x]
    asks = [x for x in (t.ask, t.close, t.last) if x]
    if not bids or not asks:
        print("no quotes; abort"); ib.disconnect(); return
    px = round((min(asks[0], max(bids[0], 0))) - 0.02, 2)  # just under ask
    o = LimitOrder("BUY", 1, px)

    trade = ib.placeOrder(aapl, o)
    print("placed", trade.orderStatus.status, "at", px)

    # Watch a couple status updates, then cancel
    deadline = time.time() + 5
    while time.time() < deadline and trade.orderStatus.status in ("PendingSubmit","PendingCancel","PreSubmitted","Submitted"):
        ib.sleep(0.25)

    print("status_before_cancel:", trade.orderStatus.status)
    ib.cancelOrder(o)
    ib.sleep(1.0)
    print("status_after_cancel:", trade.orderStatus.status)

    ib.disconnect()

if __name__ == "__main__":
    main()
