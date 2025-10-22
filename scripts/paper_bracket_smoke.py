from ib_insync import *
import os

HOST=os.getenv("IB_HOST","127.0.0.1")
PORT=int(os.getenv("IB_PORT","4002"))
CID =int(os.getenv("IB_CLIENT_ID","3021"))

ib = IB(); ib.connect(HOST, PORT, clientId=CID, timeout=25)

sym, qty = "AAPL", 1
px, tp, sl = 10.00, 10.50, 9.50  # far away => won't fill off-hours

contract = Stock(sym, "SMART", "USD")

# Build bracket (parent + TP + SL) with OCA
parent = LimitOrder("BUY", qty, px); parent.transmit = False
parent.orderId = ib.client.getReqId()

take   = LimitOrder("SELL", qty, tp)
stop   = StopOrder("SELL",  qty, sl)

take.parentId = parent.orderId
stop.parentId = parent.orderId
take.transmit = False
stop.transmit = True

oca = f"OCA_{parent.orderId}"
take.ocaGroup = stop.ocaGroup = oca
take.ocaType  = stop.ocaType  = 1  # CancelRemaining

# Place and remember the orderIds we created this run
ib.placeOrder(contract, parent)
ib.placeOrder(contract, take)
ib.placeOrder(contract, stop)
created_ids = {parent.orderId, take.orderId, stop.orderId}

ib.sleep(3)

# Snapshot trades for *our* orders
trades = [t for t in ib.trades() if t.order.orderId in created_ids]

def ts(t: Trade):
    return (t.order.orderId, t.orderStatus.status,
            t.order.action, t.order.totalQuantity,
            getattr(t.order, "lmtPrice", None),
            getattr(t.order, "auxPrice", None))

print("Trades (pre-cancel):", [ts(t) for t in trades])

# Cancel only if still active (avoid 10148 noise)
for t in trades:
    if t.isActive() and t.orderStatus.status not in ("Cancelled","ApiCancelled","Filled"):
        try:
            ib.cancelOrder(t.order)
        except Exception as e:
            # benign if already cancelled via OCA
            print(f"cancel warn {t.order.orderId}: {e}")

ib.sleep(2)

# Show remaining active among our set
left = [t for t in ib.trades() if t.order.orderId in created_ids and t.isActive()]
print("After cancel (active):", [ts(t) for t in left])

ib.disconnect()
