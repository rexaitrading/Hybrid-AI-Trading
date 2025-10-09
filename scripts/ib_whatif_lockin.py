from ib_insync import IB, Stock, LimitOrder
import os, time

SENTINEL = 1.79e308

def is_unknown(v):
    return v is None or (isinstance(v, float) and v > 1e300)

ib = IB()
ib.connect(os.getenv("IB_HOST","127.0.0.1"),
           int(os.getenv("IB_PORT","4002")),
           int(os.getenv("IB_CLIENT_ID","901")), timeout=30)

acct = ib.managedAccounts()[0]
c = Stock("AAPL","SMART","USD", primaryExchange="NASDAQ")
ib.qualifyContracts(c)

# Pick a reasonable limit (delayed ok)
ib.reqMarketDataType(3)
t = ib.reqMktData(c, "", False, False); ib.sleep(1.5)
px = (t.ask if (t.ask and t.ask>0) else (t.bid if (t.bid and t.bid>0) else 150.00))
px = round(px, 2)

o = LimitOrder("BUY", 1, px, whatIf=True)
o.account = acct
o.tif = "DAY"

trade = ib.placeOrder(c, o)

final_state = None
last_seen_placeholder = False
deadline = time.time() + 30  # wait up to 30s

while time.time() < deadline:
    ib.waitOnUpdate(timeout=0.5)  # process IB events
    # Look for OrderState in the trade log
    for e in trade.log:
        if hasattr(e, "orderState") and e.orderState:
            st = e.orderState
            # Detect placeholder vs real
            if any(is_unknown(getattr(st, fld, None)) for fld in
                   ("initMarginChange","maintMarginChange","equityWithLoanChange","commission")):
                last_seen_placeholder = True
                continue
            # Got real numbers
            final_state = st
            break
    if final_state:
        # small grace period to ensure no further updates are pending
        ib.waitOnUpdate(timeout=0.5)
        break

print("account:", acct, "limit:", px)
print("status:", trade.orderStatus.status)
if final_state:
    print("commission:", getattr(final_state, "commission", None),
          getattr(final_state, "commissionCurrency", ""))
    print("initMarginChange:", getattr(final_state, "initMarginChange", None))
    print("maintMarginChange:", getattr(final_state, "maintMarginChange", None))
    print("equityWithLoanChange:", getattr(final_state, "equityWithLoanChange", None))
else:
    print("No final what-if yet.",
          "Saw placeholder first." if last_seen_placeholder else "No placeholder either.",
          "Keeping connection longer next run.")

ib.disconnect()