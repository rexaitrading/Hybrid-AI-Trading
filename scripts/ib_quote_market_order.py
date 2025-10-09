from ib_insync import IB, Stock, LimitOrder
import os, csv, math, pathlib, json, urllib.request
from datetime import datetime, time as dtime, timedelta
from decimal import Decimal, ROUND_HALF_UP

# ------------------ utils ------------------
def d2(x): return float(Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
def valid(x):
    try: return x is not None and x>0 and not math.isnan(x)
    except: return False

def notify(msg:str):
    url = os.getenv("SLACK_WEBHOOK","").strip()
    if not url: return
    try:
        data = json.dumps({"text": msg}).encode("utf-8")
        req  = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"})
        urllib.request.urlopen(req, timeout=3)
    except Exception: pass

def get_quote(ib, c):
    t = ib.reqMktData(c, "", False, False); ib.sleep(1.0)
    bid = float(t.bid) if valid(t.bid) else None
    ask = float(t.ask) if valid(t.ask) else None
    last= float(t.last) if valid(t.last) else None
    return bid, ask, last

def tick_size(ib, c):
    try: return float(getattr(ib.reqContractDetails(c)[0], "minTick", 0.01) or 0.01)
    except Exception: return 0.01

def clamp_by_ticks(limit, ref, max_ticks, tk, side):
    ref = ref if valid(ref) else limit
    move = (limit-ref) if side=="BUY" else (ref-limit)
    max_move = max_ticks*tk
    if move > max_move:
        return d2(ref + max_move) if side=="BUY" else d2(ref - max_move)
    return limit

def now_local(): return datetime.now()

def parse_windows(spec):
    # "06:35-08:30,09:05-12:45"
    wins = []
    for chunk in (spec or "").replace(" ", "").split(","):
        if not chunk or "-" not in chunk: continue
        a,b = chunk.split("-",1)
        try:
            ah,am = map(int,a.split(":")); bh,bm = map(int,b.split(":"))
            wins.append( (dtime(ah,am), dtime(bh,bm)) )
        except: pass
    return wins

def in_windows(now_t, wins):
    if not wins: return True
    for a,b in wins:
        if a <= now_t <= b: return True
    return False

def today_realized_from_log():
    p = pathlib.Path("logs")/"orders.csv"
    if not p.exists(): return 0.0
    today = datetime.now().strftime("%Y-%m-%d")
    buys, sells = {}, {}
    with p.open("r", encoding="utf-8", errors="ignore") as f:
        rd = csv.DictReader(f)
        for r in rd:
            if (r.get("ts","").split("T")[0] != today) or (r.get("status","").upper()!="FILLED"):
                continue
            sym = (r.get("symbol") or "").upper()
            side= (r.get("side") or "").upper()
            qty = float(r.get("qty") or 0)
            avg = r.get("avgFill"); avg = float(avg) if avg not in ("",None) else None
            if avg is None or qty<=0: continue
            (buys if side=="BUY" else sells).setdefault(sym, []).append([qty,avg])
    pnl=0.0
    for s in set(list(buys.keys())+list(sells.keys())):
        b = buys.get(s,[]); a = sells.get(s,[])
        bi=si=0
        while bi<len(b) and si<len(a):
            qb,pb = b[bi]; qa,pa = a[si]
            q=min(qb,qa); pnl += q*(pa-pb)
            qb-=q; qa-=q
            if qb==0: bi+=1
            else: b[bi][0]=qb
            if qa==0: si+=1
            else: a[si][0]=qa
    return d2(pnl)

def last_loss_within_minutes(minutes:int)->bool:
    """Simple cooldown: if last *closed* round produced <0 PnL within N minutes, return True."""
    p = pathlib.Path("logs")/"orders.csv"
    if not p.exists() or minutes<=0: return False
    # naive scan: look for the last pair BUY+SELL both FILLED for same symbol today, compute realized
    today = datetime.now().strftime("%Y-%m-%d")
    rows=[]
    with p.open("r", encoding="utf-8", errors="ignore") as f:
        rd = csv.DictReader(f)
        for r in rd:
            if r.get("ts","").startswith(today) and r.get("status","").upper()=="FILLED":
                rows.append(r)
    rows.sort(key=lambda r:r["ts"])
    bysym={}
    last_loss_time=None
    for r in rows:
        s=r["symbol"].upper(); side=r["side"].upper(); q=float(r["qty"] or 0); px=float(r["avgFill"] or 0 or 0.0)
        bysym.setdefault(s,{"b":[], "s":[]})
        (bysym[s]["b"] if side=="BUY" else bysym[s]["s"]).append((datetime.fromisoformat(r["ts"]), q, px))
    for s,ds in bysym.items():
        b, a = ds["b"], ds["s"]
        bi=si=0; qbuy=qsel=0.0; pnl=0.0; close_time=None
        while bi<len(b) and si<len(a):
            tb,qb,pb = b[bi]; ta,qa,pa = a[si]
            q=min(qb,qa); pnl += q*(pa-pb)
            close_time = max(tb,ta)
            qb-=q; qa-=q
            if qb==0: bi+=1
            else: b[bi]=(tb,qb,pb)
            if qa==0: si+=1
            else: a[si]=(ta,qa,pa)
        if close_time and pnl<0:
            if (now_local()-close_time) <= timedelta(minutes=minutes):
                last_loss_time = close_time
    return last_loss_time is not None

def account_exposure_usd(ib):
    total=0.0
    for p in ib.positions():
        c = p.contract
        if getattr(c,"secType","")!="STK": continue
        qty = int(p.position)
        if qty==0: continue
        bid,ask,last = get_quote(ib,c)
        px = last or ask or bid
        if valid(px): total += abs(qty)*px
    return d2(total)

def load_symbol_floor_bps(symbol):
    """Try config/symbol_presets.yaml; fallback to hardcoded floors."""
    floors = {"AAPL":5, "MSFT":3, "NVDA":3}
    try:
        import yaml, io, pathlib
        p = pathlib.Path("config")/"symbol_presets.yaml"
        if p.exists():
            cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
            val = cfg.get(symbol.upper(),{}).get("floor_bps", None)
            if isinstance(val,(int,float)): return int(val)
    except Exception: pass
    return floors.get(symbol.upper(), 5)

def ib_daily_pnl(ib):
    acct = os.getenv("IB_ACCOUNT","").strip()
    if not acct: return None
    try:
        pnl = ib.reqPnL(acct, "")
        ib.sleep(0.6)
        val = pnl.dailyPnL
        ib.cancelPnL(pnl)
        return float(val) if val is not None else None
    except Exception:
        return None

# ------------------ guard + send ------------------
def guard_and_plan(ib, *, symbol, side, qty, tif, max_notional, tick_cap, preset_bps):
    # 0) windows
    wins = parse_windows(os.getenv("TRADE_WINDOWS","06:35-12:45"))
    if not in_windows(now_local().time(), wins):
        return False, "outside_trade_window", None

    # 1) quote sanity
    c=Stock(symbol,"SMART","USD"); ib.qualifyContracts(c)
    bid,ask,last = get_quote(ib,c)
    if os.getenv("ABORT_IF_NO_QUOTE","true").lower() in ("1","true","yes"):
        if not (valid(bid) or valid(ask)):
            return False, "no_live_bid_or_ask", None

    # 2) spread guard
    spread_bps=None
    if valid(bid) and valid(ask):
        mid=(bid+ask)/2.0
        if valid(mid):
            spread_bps = (ask-bid)/mid*10_000.0
            if spread_bps > float(os.getenv("MAX_SPREAD_BPS","8")):
                return False, f"wide_spread_{spread_bps:.1f}bps", None

    # 3) PnL guard
    max_loss = float(os.getenv("MAX_DAILY_LOSS_USD","300"))
    pnl_ib = ib_daily_pnl(ib)
    pnl_today = pnl_ib if pnl_ib is not None else today_realized_from_log()
    if pnl_today < -max_loss:
        return False, f"daily_loss_exceeded_{pnl_today}", None

    # 4) exposure cap
    max_expo = float(os.getenv("MAX_EXPOSURE_USD","5000"))
    expo = account_exposure_usd(ib)
    if expo > max_expo:
        return False, f"exposure_exceeded_{expo}", None

    # 5) cooldown after loss
    cool_min = int(os.getenv("COOLDOWN_MIN","0") or 0)
    if cool_min>0 and last_loss_within_minutes(cool_min):
        return False, f"cooldown_active_{cool_min}m", None

    # 6) adaptive bps
    adapt_k = float(os.getenv("ADAPTIVE_SPREAD_FACTOR","0.5"))
    eff_bps = preset_bps
    if spread_bps is not None:
        eff_bps = max(preset_bps, int(round(adapt_k*spread_bps)))
    max_slip = int(os.getenv("MAX_SLIPPAGE_BPS","20"))
    eff_bps = min(eff_bps, max_slip)

    # 7) limit with tick clamp
    tk=tick_size(ib,c)
    bps = eff_bps/10_000.0
    if side=="BUY":
        base = ask if valid(ask) else last
        if not valid(base): return False, "no_ask_or_last", None
        raw = d2(base*(1+bps)); ref = ask if valid(ask) else base
        limit = clamp_by_ticks(raw, ref, tick_cap, tk, "BUY")
    else:
        base = bid if valid(bid) else last
        if not valid(base): return False, "no_bid_or_last", None
        raw = d2(base*(1-bps)); ref = bid if valid(bid) else base
        limit = clamp_by_ticks(raw, ref, tick_cap, tk, "SELL")

    notional = d2(limit*qty)
    if notional<=0 or notional>max_notional:
        return False, f"invalid_or_cap_notional_{notional}", None

    plan = {"contract":c, "bid":bid, "ask":ask, "last":last, "tk":tk,
            "limit":limit, "notional":notional, "eff_bps":eff_bps}
    return True, "", plan

def log_row(symbol, side, qty, bid, ask, last, limit, status, filled, avgFill, note):
    p = pathlib.Path("logs"); p.mkdir(exist_ok=True)
    f = p/"orders.csv"; new = not f.exists()
    with f.open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new: w.writerow(["ts","symbol","side","qty","bid","ask","last","limit","status","filled","avgFill","note"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), symbol, side, qty, bid, ask, last, limit, status, filled, avgFill, note])

def main():
    host=os.getenv("IB_HOST","127.0.0.1"); port=int(os.getenv("IB_PORT","7497")); cid=int(os.getenv("IB_CLIENT_ID","201"))
    symbol=os.getenv("SYMBOL","AAPL").upper()
    side=os.getenv("SIDE","BUY").upper()
    qty=int(os.getenv("QTY","1"))
    preset_bps=int(os.getenv("SLIPPAGE_BPS","5"))
    tif=os.getenv("TIF","IOC")
    tick_cap=int(os.getenv("TICK_CAP","20"))
    max_notional=float(os.getenv("MAX_NOTIONAL_USD","100000"))
    keep_open=os.getenv("KEEP_OPEN","false").lower() in ("1","true","yes")
    outside_rth=os.getenv("OUTSIDE_RTH","true").lower() in ("1","true","yes")

    # symbol floor override
    floor_bps = load_symbol_floor_bps(symbol)
    preset_bps = max(preset_bps, floor_bps)

    ib=IB(); print(f"[CONNECT] {host}:{port} clientId={cid}"); ib.connect(host,port,clientId=cid)
    try:
        ok, reason, plan = guard_and_plan(ib, symbol=symbol, side=side, qty=qty, tif=tif,
                                          max_notional=max_notional, tick_cap=tick_cap, preset_bps=preset_bps)
        if not ok:
            print(f"[ABORT] Guard blocked: {reason}")
            log_row(symbol, side, qty, None, None, None, None, "ABORT", 0, "", reason)
            notify(f"ABORT {symbol} {side} x{qty}: {reason}")
            return

        c, limit, notional = plan["contract"], plan["limit"], plan["notional"]
        bid,ask,last = plan["bid"], plan["ask"], plan["last"]
        eff_bps = plan["eff_bps"]

        print(f"[PLAN] {side} {qty} {symbol} @ ~{limit} (TIF={tif}) notional≈${notional:,.2f}  [eff_bps={eff_bps}]")
        tr = ib.placeOrder(c, LimitOrder(side, qty, limit, tif=tif, outsideRth=outside_rth))
        print("[SUBMIT] sent, waiting...")
        for _ in range(30):
            ib.sleep(0.2)
            if tr.orderStatus.status in ("Filled","Cancelled","Inactive"): break

        status = tr.orderStatus.status
        filled = tr.orderStatus.filled
        avgFill = tr.orderStatus.avgFillPrice
        print(f"[RESULT] status={status} filled={filled} avgFill={avgFill}")
        log_row(symbol, side, qty, bid, ask, last, limit, status, filled, avgFill, f"eff_bps={eff_bps}")
        if status=="Filled":
            notify(f"FILLED {symbol} {side} x{qty} @ {avgFill}")
        elif status=="Cancelled":
            notify(f"CANCELLED {symbol} {side} x{qty} plan {limit}")
    finally:
        if keep_open:
            print("[KEEP-OPEN] Session active; press Ctrl+C to exit.")
            try:
                while True: ib.sleep(1)
            except KeyboardInterrupt: pass
        ib.disconnect(); print("[DONE] disconnected.")

if __name__=="__main__": main()
