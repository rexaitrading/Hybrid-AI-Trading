from ib_insync import IB, Stock, LimitOrder
import os, time, math

SENTINEL = 1.79e308

def is_bad(v):
    return v is None or (isinstance(v, float) and v > 1e300)

def pick(state, name, alt):
    v = getattr(state, name, None)
    return v if not is_bad(v) else getattr(state, alt, None)

def have_final(state):
    # Prefer initMargin/maintMargin; fall back to *Change if needed
    im = pick(state, "initMargin", "initMarginChange")
    mm = pick(state, "maintMargin", "maintMarginChange")
    return not (is_bad(im) or is_bad(mm))

def extract(state):
    im = pick(state, "initMargin", "initMarginChange")
    mm = pick(state, "maintMargin", "maintMarginChange")
    ewl = pick(state, "equityWithLoan", "equityWithLoanChange")
    cc = getattr(state, "commissionCurrency", "")
    cm = getattr(state, "commission", None)
    mn = getattr(state, "minCommission", None)
    mx = getattr(state, "maxCommission", None)
    st = getattr(state, "status", None)
    return st, cm, cc, im, mm, ewl, mn, mx

ib = IB()
ib.connect(os.getenv("IB_HOST","127.0.0.1"),
           int(os.getenv("IB_PORT","4002")),
           int(os.getenv("IB_CLIENT_ID","901")), timeout=30)

acct = ib.managedAccounts()[0]
c = Stock("AAPL","SMART","USD", primaryExchange="NASDAQ")
ib.qualifyContracts(c)

# Use delayed data to anchor a sane price
ib.reqMarketDataType(3)
t = ib.reqMktData(c, "", False, False); ib.sleep(1.5)
base_px = t.ask if (t.ask and t.ask>0) else (t.bid if (t.bid and t.bid>0) else 150.00)
base_px = round(base_px, 2)

best = None
for attempt in range(10):
    px = round(base_px + attempt*0.01, 2)  # tiny nudge to avoid caching
    o = LimitOrder("BUY", 1, px); o.account = acct; o.tif="DAY"
    st = ib.whatIfOrder(c, o)
    if have_final(st):
        best = st
        print(f"[pass {attempt+1}] FINAL at {px}")
        break
    else:
        print(f"[pass {attempt+1}] placeholder at {px}; waiting …")
        ib.waitOnUpdate(timeout=1.0)

if best is None:
    # one last settle + final try at base price
    ib.waitOnUpdate(timeout=1.5)
    o = LimitOrder("BUY", 1, base_px); o.account = acct; o.tif="DAY"
    best = ib.whatIfOrder(c, o)

status, commission, commCcy, initM, maintM, eqLoan, minC, maxC = extract(best) if best else (None,)*8

print("account:", acct, "base_limit:", base_px)
print("status:", status)
print("commission:", commission, commCcy)
print("initMargin:", initM)
print("maintMargin:", maintM)
print("equityWithLoan:", eqLoan)
print("min/max commission:", minC, maxC)

ib.waitOnUpdate(timeout=1.0)
ib.disconnect()