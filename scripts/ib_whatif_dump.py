from ib_insync import IB, Stock, LimitOrder
import os, time, json, math

def as_plain(o):
    try:
        return {k: (str(v) if not isinstance(v, (int,float,str)) else v)
                for k,v in vars(o).items()}
    except Exception:
        return str(o)

ib = IB()
ib.connect(os.getenv("IB_HOST","127.0.0.1"),
           int(os.getenv("IB_PORT","4002")),
           int(os.getenv("IB_CLIENT_ID","901")), timeout=30)

acct = ib.managedAccounts()[0]
c = Stock("AAPL","SMART","USD", primaryExchange="NASDAQ"); ib.qualifyContracts(c)

ib.reqMarketDataType(3)
t = ib.reqMktData(c, "", False, False); ib.sleep(1.5)
base_px = t.ask if (t.ask and t.ask>0) else (t.bid if (t.bid and t.bid>0) else 150.00)
base_px = round(base_px, 2)
print("account:", acct, "base_limit:", base_px)

# ---------- A) whatIfOrder() dump ----------
o = LimitOrder("BUY", 1, base_px); o.account = acct; o.tif="DAY"
st = ib.whatIfOrder(c, o)
print("\n[A] whatIfOrder immediate dump:")
print(type(st).__name__)
print(json.dumps(as_plain(st), indent=2))

ib.waitOnUpdate(timeout=1.0)
st2 = ib.whatIfOrder(c, o)
print("\n[A] whatIfOrder after 1s dump:")
print(type(st2).__name__)
print(json.dumps(as_plain(st2), indent=2))

# ---------- B) whatIf=True (event-driven) dump ----------
o2 = LimitOrder("BUY", 1, base_px, whatIf=True); o2.account = acct; o2.tif="DAY"
trade = ib.placeOrder(c, o2)
seen = set()
print("\n[B] whatIf=True event log stream (up to 20s):")
deadline = time.time() + 20
while time.time() < deadline:
    ib.waitOnUpdate(timeout=0.5)
    for e in trade.log:
        if id(e) in seen: 
            continue
        seen.add(id(e))
        ev = getattr(e, "event", None)
        print(f"- logEntry: {type(e).__name__}  -> event: {type(ev).__name__ if ev else None}")
        if ev and hasattr(ev, "orderState") and ev.orderState:
            print("  orderState fields:")
            print(json.dumps(as_plain(ev.orderState), indent=2))
            # stop early if we already see real numbers
            try:
                im = float(getattr(ev.orderState, "initMargin", "nan"))
                mm = float(getattr(ev.orderState, "maintMargin", "nan"))
                if im < 1e300 and mm < 1e300:
                    print("  (looks FINAL; stopping stream)")
                    raise SystemExit
            except Exception:
                pass

ib.disconnect()