import os
import time

from ib_insync import IB, LimitOrder, Stock

SENTINEL = 1.7976931348623157e308


def to_float(x):
    try:
        return float(str(x)) if x not in (None, "", "nan", "None") else None
    except Exception:
        return None


def is_bad(v):
    return v is None or (isinstance(v, float) and v > 1e300)


def pick_num(st, *names):
    for n in names:
        v = to_float(getattr(st, n, None))
        if not is_bad(v):
            return v
    return None


ib = IB()
ib.connect(
    os.getenv("IB_HOST", "127.0.0.1"),
    int(os.getenv("IB_PORT", "4002")),
    int(os.getenv("IB_CLIENT_ID", "901")),
    timeout=30,
)

acct = ib.managedAccounts()[0]
c = Stock("AAPL", "SMART", "USD", primaryExchange="NASDAQ")
ib.qualifyContracts(c)

# anchor price (delayed ok)
ib.reqMarketDataType(3)
t = ib.reqMktData(c, "", False, False)
ib.sleep(1.5)
px = t.ask if (t.ask and t.ask > 0) else (t.bid if (t.bid and t.bid > 0) else 150.00)
px = round(px, 2)

# --- Place WHAT-IF order ---
o = LimitOrder("BUY", 1, px, whatIf=True)
o.account = acct
o.tif = "DAY"
trade = ib.placeOrder(c, o)

# --- Pull final OrderState via openOrders refresh loop ---
final_state = None
deadline = time.time() + 20
while time.time() < deadline and final_state is None:
    ib.reqOpenOrders()  # force an openOrders snapshot/refresh
    ib.waitOnUpdate(timeout=0.5)

    # scan all known trades for a whatIf orderstate
    for tr in ib.trades():
        st = getattr(tr, "orderState", None) or None
        if not st:  # some builds hang it on tr.log events
            for e in tr.log:
                ev = getattr(e, "event", None)
                st = getattr(ev, "orderState", None) or st

        if not st:
            continue

        # Look across IB's many field names; your dump shows *Before/Change/After* strings
        initM = pick_num(st, "initMargin", "initMarginAfter", "initMarginChange")
        maintM = pick_num(st, "maintMargin", "maintMarginAfter", "maintMarginChange")

        if not is_bad(initM) and not is_bad(maintM):
            final_state = st
            break

if final_state:
    im = pick_num(final_state, "initMargin", "initMarginAfter", "initMarginChange")
    mm = pick_num(final_state, "maintMargin", "maintMarginAfter", "maintMarginChange")
    ewl = pick_num(final_state, "equityWithLoan", "equityWithLoanAfter", "equityWithLoanChange")
    com = to_float(getattr(final_state, "commission", None))
    ccy = getattr(final_state, "commissionCurrency", "") or ""
    print("account:", acct, "limit:", px)
    print("status:", getattr(final_state, "status", None))
    print("commission:", com, ccy)
    print("initMargin:", im)
    print("maintMargin:", mm)
    print("equityWithLoan:", ewl)
else:
    print("Could not fetch final OrderState via reqOpenOrders within timeout.")

ib.disconnect()
