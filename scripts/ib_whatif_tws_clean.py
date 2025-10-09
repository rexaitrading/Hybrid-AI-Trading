from ib_insync import IB, Stock, LimitOrder
import os, time

def f(x):
    try: return float(str(x))
    except: return None

def is_final(v):  # not DBL_MAX
    return v is not None and v < 1e300

def pick(st, *names):
    for n in names:
        v = f(getattr(st, n, None))
        if is_final(v): return v
    return None

ib = IB()
ib.connect("127.0.0.1", 7497, clientId=902, timeout=30)

acct = ib.managedAccounts()[0]
c = Stock("AAPL","SMART","USD", primaryExchange="NASDAQ")
ib.qualifyContracts(c)

ib.reqMarketDataType(3)  # delayed ok
t = ib.reqMktData(c, "", False, False); ib.sleep(1.5)
px = t.ask if (t.ask and t.ask>0) else (t.bid if (t.bid and t.bid>0) else 150.00)
px = round(px, 2)

o = LimitOrder("BUY", 1, px, whatIf=True); o.account = acct; o.tif = "DAY"
trade = ib.placeOrder(c, o)

final = None
deadline = time.time() + 30
while time.time() < deadline and final is None:
    ib.reqOpenOrders()           # nudge TWS to push current order state
    ib.waitOnUpdate(0.5)         # keep socket alive & process events
    st = trade.orderState
    if st:
        initM  = pick(st, "initMargin",  "initMarginAfter",  "initMarginChange")
        maintM = pick(st, "maintMargin", "maintMarginAfter", "maintMarginChange")
        if is_final(initM) and is_final(maintM):
            final = (st, initM, maintM)

print("account:", acct, "limit:", px)
if final:
    st, initM, maintM = final
    eqLoan = pick(st, "equityWithLoan","equityWithLoanAfter","equityWithLoanChange")
    print("status:", getattr(st,"status",None))
    print("commission:", f(getattr(st,"commission",None)), getattr(st,"commissionCurrency",""))
    print("initMargin:", initM)
    print("maintMargin:", maintM)
    print("equityWithLoan:", eqLoan)
else:
    print("Still no final OrderState seen (check that only TWS is running).")

ib.disconnect()