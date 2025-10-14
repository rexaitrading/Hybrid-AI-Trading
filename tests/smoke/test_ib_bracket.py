from ib_insync import *
import os

HOST=os.getenv("IB_HOST","127.0.0.1")
PORT=int(os.getenv("IB_PORT","4002"))
CID =int(os.getenv("IB_CLIENT_ID","3021"))

def _ts(t: Trade):
    return (t.order.orderId, t.orderStatus.status, t.order.action, t.order.totalQuantity)

def test_bracket_create_and_cleanup():
    ib = IB(); ib.connect(HOST, PORT, clientId=CID, timeout=25)

    sym, qty = "AAPL", 1
    px, tp, sl = 10.00, 10.50, 9.50  # far from market

    c = Stock(sym, "SMART", "USD")
    parent = LimitOrder("BUY", qty, px); parent.transmit=False
    parent.orderId = ib.client.getReqId()
    take   = LimitOrder("SELL", qty, tp);  take.parentId = parent.orderId; take.transmit=False
    stop   = StopOrder("SELL",  qty, sl);  stop.parentId = parent.orderId; stop.transmit=True
    oca = f"OCA_{parent.orderId}"; take.ocaGroup = stop.ocaGroup = oca; take.ocaType = stop.ocaType = 1

    ib.placeOrder(c, parent); ib.placeOrder(c, take); ib.placeOrder(c, stop)
    created = {parent.orderId, take.orderId, stop.orderId}
    ib.sleep(3)

    trades = [t for t in ib.trades() if t.order.orderId in created]
    assert len(trades) == 3, f"Expected 3 trades, got {len(trades)} -> {[_ts(t) for t in trades]}"

    # cancel only if still active
    for t in trades:
        if t.isActive() and t.orderStatus.status not in ("Cancelled","ApiCancelled","Filled"):
            try: ib.cancelOrder(t.order)
            except Exception: pass
    ib.sleep(2)

    left = [t for t in ib.trades() if t.order.orderId in created and t.isActive()]
    assert not left, f"Left active: {[_ts(t) for t in left]}"
    ib.disconnect()
