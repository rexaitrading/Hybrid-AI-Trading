import time
from ib_insync import IB

def gc_stale_orders(ib: IB, max_age_sec=60):
    now = time.time()
    for t in ib.openTrades():
        s = t.orderStatus
        if s.status == "Submitted":
            age = now - t.log[-1].time.timestamp() if t.log else 0
            if age > max_age_sec:
                ib.cancelOrder(t.order)
