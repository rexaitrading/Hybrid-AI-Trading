import os, math, tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from ib_insync import IB, Stock, LimitOrder, util

# ---------- helpers ----------
def valid(x):
    try: return x is not None and x>0 and not math.isnan(x)
    except: return False

def log(msg):
    out.configure(state="normal"); out.insert("end", msg+"\n"); out.see("end"); out.configure(state="disabled")

def get_yaml_floor(symbol):
    try:
        import yaml, pathlib
        p = pathlib.Path("config")/"symbol_presets.yaml"
        if p.exists():
            cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
            v = cfg.get(symbol.upper(),{}).get("floor_bps", None)
            if v is not None: return int(v)
    except Exception:
        pass
    return 5 if symbol.upper()=="AAPL" else 3

def _min_tick(c, ib):
    try:
        det = ib.reqContractDetails(c)[0]
        mt = getattr(det, "minTick", 0.01) or 0.01
        return float(mt)
    except Exception:
        return 0.01

def _clamp(limit, ref, tick_cap, tk, side):
    ref = ref if valid(ref) else limit
    move = (limit-ref) if side=="BUY" else (ref-limit)
    max_move = tick_cap*tk
    if move > max_move:
        return round(ref + max_move, 2) if side=="BUY" else round(ref - max_move, 2)
    return limit

# ---------- IB connect ----------
ib = None
def connect():
    global ib
    try:
        host = os.getenv("IB_HOST","127.0.0.1")
        port = int(os.getenv("IB_PORT","7497"))
        cid  = int(os.getenv("IB_CLIENT_ID","201"))
        ib = IB(); ib.connect(host, port, clientId=cid)
        btnConnect.configure(state="disabled"); btnDisconnect.configure(state="normal")
        log(f"[CONNECT] {host}:{port} clientId={cid}")
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        log(f"[ERROR] Connect failed: {err}")
        messagebox.showerror("Connect", err)

def disconnect():
    try:
        ib.disconnect()
        btnConnect.configure(state="normal"); btnDisconnect.configure(state="disabled")
        log("[DONE] disconnected.")
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        log(f"[ERROR] Disconnect failed: {err}")
        messagebox.showerror("Disconnect", err)

# ---------- actions ----------
def quote_only():
    sym = symVar.get().strip().upper() or "AAPL"
    c = Stock(sym,"SMART","USD"); ib.qualifyContracts(c)
    t = ib.reqMktData(c, "", False, False); ib.sleep(1.0)
    bid = float(t.bid) if valid(t.bid) else None
    ask = float(t.ask) if valid(t.ask) else None
    last= float(t.last) if valid(t.last) else None
    log(f"[QUOTE] {sym}  bid={bid}  ask={ask}  last={last}")

def _limit_from_quote(sym, side, bps, tick_cap=20):
    c = Stock(sym,"SMART","USD"); ib.qualifyContracts(c)
    t = ib.reqMktData(c, "", False, False); ib.sleep(1.0)
    bid = float(t.bid) if valid(t.bid) else None
    ask = float(t.ask) if valid(t.ask) else None
    last= float(t.last) if valid(t.last) else None

    if os.getenv("ABORT_IF_NO_QUOTE","true").lower() in ("1","true","yes"):
        if not (valid(bid) or valid(ask)):
            return c, bid, ask, last, None

    eff = max(int(bps), get_yaml_floor(sym))
    tkSize = _min_tick(c, ib)

    if side=="BUY":
        base = ask if valid(ask) else last
        if not valid(base): return c, bid, ask, last, None
        raw = round(base*(1+eff/10_000.0),2)
        ref = ask if valid(ask) else base
        limit = _clamp(raw, ref, tick_cap, tkSize, side)
    else:
        base = bid if valid(bid) else last
        if not valid(base): return c, bid, ask, last, None
        raw = round(base*(1-eff/10_000.0),2)
        ref = bid if valid(bid) else base
        limit = _clamp(raw, ref, tick_cap, tkSize, side)

    return c, bid, ask, last, (limit, eff)

def send(side):
    sym = symVar.get().strip().upper() or "AAPL"
    try: qty = int(qtyVar.get() or "1")
    except: qty = 1
    try: bps = int(bpsVar.get() or "5")
    except: bps = 5
    tif = os.getenv("TIF","IOC")
    c, bid, ask, last, res = _limit_from_quote(sym, side, bps)
    log(f"[QUOTE] {sym}  bid={bid}  ask={ask}  last={last}")
    if res is None:
        log("[ABORT] No usable quote (after-hours or missing)."); return
    limit, eff_bps = res
    notional = round(limit*qty,2)
    max_notional = float(os.getenv("MAX_NOTIONAL_USD","100000"))
    if notional<=0 or notional>max_notional:
        log(f"[ABORT] Notional invalid/capped: {notional} > {max_notional}"); return
    order = LimitOrder(side, qty, limit, tif=tif, outsideRth=os.getenv("OUTSIDE_RTH","true").lower() in ("1","true","yes"))
    tr = ib.placeOrder(c, order)
    log(f"[PLAN] {side} {qty} {sym} @ ~{limit} (TIF={tif}) notional≈${notional:,.2f} [eff_bps={eff_bps}]")
    log("[SUBMIT] sent, waiting...")
    for _ in range(30):
        ib.sleep(0.2)
        if tr.orderStatus.status in ("Filled","Cancelled","Inactive"): break
    log(f"[RESULT] status={tr.orderStatus.status} filled={tr.orderStatus.filled} avgFill={tr.orderStatus.avgFillPrice}")

def flatten_symbol():
    sym = symVar.get().strip().upper() or "AAPL"
    send("SELL")

# ---------- UI (dark theme) ----------
util.startLoop()
root = tk.Tk(); root.title("GUI Trading Console (Paper IOC)")

# Dark palette
BG      = "#0f172a"   # slate-900
PANEL   = "#111827"   # gray-900
ENTRYBG = "#1f2937"   # gray-800
BTN     = "#1f2937"
BTN_H   = "#374151"   # gray-700
FG      = "#e5e7eb"   # gray-200
ACCENT  = "#60a5fa"   # blue-400

style = ttk.Style()
style.theme_use("clam")
# Base
style.configure(".", background=BG, foreground=FG)
style.configure("TFrame", background=BG)
style.configure("TLabel", background=BG, foreground=FG)
# Entry
style.configure("TEntry", fieldbackground=ENTRYBG, foreground=FG, bordercolor=ENTRYBG, lightcolor=ENTRYBG, darkcolor=ENTRYBG)
# Buttons
style.configure("TButton", background=BTN, foreground=FG, borderwidth=0, focusthickness=0, padding=6)
style.map("TButton", background=[("active", BTN_H)])
root.configure(bg=BG)

frm = ttk.Frame(root, padding=8); frm.grid(sticky="nsew"); root.rowconfigure(0, weight=1); root.columnconfigure(0, weight=1)

symVar = tk.StringVar(value="AAPL")
qtyVar = tk.StringVar(value="1")
bpsVar = tk.StringVar(value=os.getenv("SLIPPAGE_BPS","5") or "5")

row=0
ttk.Label(frm, text="Symbol").grid(row=row, column=0, sticky="w")
ttk.Entry(frm, textvariable=symVar, width=12).grid(row=row, column=1, sticky="w")
ttk.Label(frm, text="Qty").grid(row=row, column=2, sticky="w")
ttk.Entry(frm, textvariable=qtyVar, width=8).grid(row=row, column=3, sticky="w")
ttk.Label(frm, text="BPS").grid(row=row, column=4, sticky="w")
ttk.Entry(frm, textvariable=bpsVar, width=8).grid(row=row, column=5, sticky="w")
topVar = tk.BooleanVar(value=False)
ttk.Checkbutton(frm, text="Stay on top", variable=topVar,
                command=lambda: root.attributes("-topmost", topVar.get())).grid(row=row, column=6, padx=6, sticky="w")

row+=1
btnConnect=ttk.Button(frm, text="Connect", command=connect); btnConnect.grid(row=row, column=0, pady=6, sticky="we")
btnDisconnect=ttk.Button(frm, text="Disconnect", command=disconnect, state="disabled"); btnDisconnect.grid(row=row, column=1, pady=6, sticky="we")
ttk.Button(frm, text="Quote",  command=quote_only).grid(row=row, column=2, pady=6, sticky="we")
ttk.Button(frm, text="BUY (IOC)",  command=lambda: send("BUY")).grid(row=row, column=3, pady=6, sticky="we")
ttk.Button(frm, text="SELL (IOC)", command=lambda: send("SELL")).grid(row=row, column=4, pady=6, sticky="we")
ttk.Button(frm, text="Flatten",    command=flatten_symbol).grid(row=row, column=5, pady=6, sticky="we")

row+=1
out = scrolledtext.ScrolledText(frm, height=16, width=100, state="disabled"); out.grid(row=row, column=0, columnspan=7, sticky="nsew")
out.configure(bg=PANEL, fg=FG, insertbackground=FG, highlightthickness=0)

frm.rowconfigure(row, weight=1)

# Auto-connect shortly after launch
root.after(250, connect)
root.mainloop()
