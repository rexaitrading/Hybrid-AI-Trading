from ib_insync import IB, Stock, LimitOrder
import os, time, math

SENTINEL = 1.7976931348623157e308

def to_float(x):
    if x is None: return None
    if isinstance(x, (int, float)): return float(x)
    try:
        s = str(x).strip()
        if s == "" or s.lower() in ("nan","none"): return None
        return float(s)
    except Exception:
        return None

def is_sentinel(v):
    return v is None or (isinstance(v, float) and v > 1e300)

def pick_num(state, primary, alt=None):
    v = to_float(getattr(state, primary, None))
    if is_sentinel(v) and alt:
        v2 = to_float(getattr(state, alt, None))
        return v2
    return v

def margins_ready(state):
    im = pick_num(state, "initMargin", "initMarginChange")
    mm = pick_num(state, "maintMargin", "maintMarginChange")
    return (not is_sentinel(im)) and (not is_sentinel(mm))

def summarize(tag, state):
    im = pick_num(state, "initMargin", "initMarginChange")
    mm = pick_num(state, "maintMargin", "maintMarginChange")
    ewl = pick_num(state, "equityWithLoan", "equityWithLoanChange")
    cm  = to_float(getattr(state, "commission", None))
    ccy = getattr(state, "commissionCurrency", "") or ""
    st  = getattr(state, "status", None)
    print(tag)
    print("status:", st)
    print("commission:", cm, ccy)
    print("initMargin:", im)
    print("maintMargin:", mm)
    print("equityWithLoan:", ewl)

ib = IB()
ib.connect(os.getenv("IB_HOST","127.0.0.1"),
           int(os.getenv("IB_PORT","4002")),
           int(os.getenv("IB_CLIENT_ID","901")), timeout=30)

acct = ib.managedAccounts()[0]
c = Stock("AAPL","SMART","USD", primaryExchange="NASDAQ")
ib.qualifyContracts(c)

# Price anchor (delayed ok)
ib.reqMarketDataType(3)
t = ib.reqMktData(c, "", False, False); ib.sleep(1.5)
base_px = t.ask if (t.ask and t.ask>0) else (t.bid if (t.bid and t.bid>0) else 150.00)
base_px = round(base_px, 2)

print("account:", acct, "base_limit:", base_px)

# ---- Phase 1: event-driven whatIf (best source) ----
o = LimitOrder("BUY", 1, base_px, whatIf=True)
o.account = acct; o.tif = "DAY"
trade = ib.placeOrder(c, o)

final_state = None
deadline = time.time() + 30
while time.time() < deadline and final_state is None:
    ib.waitOnUpdate(timeout=0.5)
    for entry in list(trade.log):
        ev = getattr(entry, "event", None)
        st = getattr(ev, "orderState", None)
        if st and margins_ready(st):
            final_state = st
            summarize("[event-driven FINAL]", st)
            break

# ---- Phase 2: fallback poller (re-issue whatIfOrder with jitter) ----
if final_state is None:
    for attempt in range(10):
        px = round(base_px + 0.01*attempt, 2)
        o2 = LimitOrder("BUY", 1, px); o2.account = acct; o2.tif="DAY"
        st2 = ib.whatIfOrder(c, o2)
        if margins_ready(st2):
            summarize(f"[poller FINAL pass {attempt+1} at {px}]", st2)
            final_state = st2
            break
        else:
            print(f"[poller pass {attempt+1}] placeholder at {px}; waiting …")
            ib.waitOnUpdate(timeout=1.0)

if final_state is None:
    # One last settle + base retry
    ib.waitOnUpdate(timeout=1.5)
    st3 = ib.whatIfOrder(c, LimitOrder("BUY", 1, base_px, account=acct, tif="DAY"))
    if margins_ready(st3):
        summarize("[poller FINAL last try]", st3)
        final_state = st3

if final_state is None:
    print("Still placeholder margins after retries. (Gateway logs show finals; client will on next run.)")

ib.waitOnUpdate(timeout=1.0)
ib.disconnect()