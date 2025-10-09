import os
import time

from ib_insync import IB, LimitOrder, Stock


def is_unknown(v):
    return v is None or (isinstance(v, float) and v > 1e300)  # DBL_MAX sentinel


ib = IB()
ib.connect(
    os.getenv("IB_HOST", "127.0.0.1"),
    int(os.getenv("IB_PORT", "4002")),
    int(os.getenv("IB_CLIENT_ID", "901")),
    timeout=30,
)

acct = ib.managedAccounts()[0]

# Contract
c = Stock("AAPL", "SMART", "USD", primaryExchange="NASDAQ")
ib.qualifyContracts(c)

# Use delayed data to pick a sane price
ib.reqMarketDataType(3)
t = ib.reqMktData(c, "", False, False)
ib.sleep(1.5)
px = t.ask if (t.ask and t.ask > 0) else (t.bid if (t.bid and t.bid > 0) else 150.00)
px = round(px, 2)

# Place a What-If order (event-driven path)
o = LimitOrder("BUY", 1, px, whatIf=True)
o.account = acct
o.tif = "DAY"

trade = ib.placeOrder(c, o)

final_state = None
saw_placeholder = False
deadline = time.time() + 30  # wait up to 30s

while time.time() < deadline and final_state is None:
    # Process IB events (keeps socket alive)
    ib.waitOnUpdate(timeout=0.5)

    # IMPORTANT: log entries hold an .event; get .event.orderState
    for entry in list(trade.log):
        ev = getattr(entry, "event", None)
        st = getattr(ev, "orderState", None)
        if st:
            # Skip placeholder (DBL_MAX)
            if any(
                is_unknown(getattr(st, fld, None))
                for fld in (
                    "initMarginChange",
                    "maintMarginChange",
                    "equityWithLoanChange",
                    "commission",
                )
            ):
                saw_placeholder = True
                continue
            final_state = st
            break

# small grace to let any last updates land
if final_state is None:
    ib.waitOnUpdate(timeout=1.0)
    for entry in list(trade.log):
        ev = getattr(entry, "event", None)
        st = getattr(ev, "orderState", None)
        if st and not any(
            is_unknown(getattr(st, fld, None))
            for fld in (
                "initMarginChange",
                "maintMarginChange",
                "equityWithLoanChange",
                "commission",
            )
        ):
            final_state = st
            break

print("account:", acct, "limit:", px)
print("status:", trade.orderStatus.status)
if final_state:
    print(
        "commission:",
        getattr(final_state, "commission", None),
        getattr(final_state, "commissionCurrency", ""),
    )
    print("initMarginChange:", getattr(final_state, "initMarginChange", None))
    print("maintMarginChange:", getattr(final_state, "maintMarginChange", None))
    print("equityWithLoanChange:", getattr(final_state, "equityWithLoanChange", None))
else:
    print(
        "No final what-if yet.",
        (
            "Saw placeholder first."
            if saw_placeholder
            else "No placeholder seen. Will keep alive longer next run."
        ),
    )

ib.disconnect()
