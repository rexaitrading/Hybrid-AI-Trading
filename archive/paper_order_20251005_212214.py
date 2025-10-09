from ib_insync import StopLimitOrder
"""
Paper Order Orchestrator (Hybrid AI Quant Pro v36.0)
----------------------------------------------------
Phase 1 + 2: Protective LIMIT (tick clamp), Adaptive, Bracket OCO, Dedupe,
Spread/Session/Early-open guards, What-If, Auto-reprice, Risk-based sizing,
Cooldowns, JSONL audit, optional Slack alerts.
"""
from __future__ import annotations

import argparse, json, os, sys, time, urllib.request, urllib.error
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None  # degrade gracefully

from ib_insync import IB, Stock, Contract, Trade, LimitOrder, StopOrder, TagValue

ROOT = Path.cwd()
LOGS = ROOT / "logs"
STATE = ROOT / "state"
CONTROL = ROOT / "control"
for d in (LOGS, STATE, CONTROL): d.mkdir(parents=True, exist_ok=True)

JSONL_ORDERS = LOGS / "orders.jsonl"
COOLDOWNS    = STATE / "cooldowns.json"
PAUSE_FLAG   = CONTROL / "PAUSE"

def _jsonl_write(path: Path, obj: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def _slack_alert(text: str, webhook: Optional[str]) -> None:
    if not webhook: return
    try:
        data = json.dumps({"text": text}).encode("utf-8")
        req = urllib.request.Request(webhook, data=data, headers={"Content-Type":"application/json"})
        urllib.request.urlopen(req, timeout=5).read()
    except Exception:
        pass  # non-fatal

@dataclass
class Quotes:
    bid: Optional[float]; ask: Optional[float]; last: Optional[float]; close: Optional[float]; minTick: float

def get_min_tick(ib: IB, contract: Contract) -> float:
    cds = ib.reqContractDetails(contract)
    if not cds: raise RuntimeError("No contract details")
    return float(cds[0].minTick or 0.01)

def get_quotes(ib: IB, contract: Contract) -> Quotes:
    mt = get_min_tick(ib, contract)
    tk = ib.reqMktData(contract, "", False, False); ib.sleep(1.5)
    bid = getattr(tk, "bid", None); ask = getattr(tk, "ask", None)
    last = getattr(tk, "last", None); close = getattr(tk, "close", None)
    if (not last) and hasattr(tk, "marketPrice"):
        try:
            mp = tk.marketPrice()
            if mp and mp > 0: last = mp
        except Exception: pass
    return Quotes(bid, ask, last, close, mt)

def clamp_limit(side: str, q: Quotes, slip_pct: float, ticks_clamp: int, fallback_ticks: int) -> float:
    side = side.upper(); tick = max(q.minTick, 0.01)
    if side == "BUY":
        base = q.ask if (q.ask and q.ask > 0) else (q.last or q.close or 10.0)
        desired = base * (1.0 + slip_pct)
        px = min(desired, (q.ask + (ticks_clamp - 1) * tick) if (q.ask and q.ask > 0) else base + max(fallback_ticks,1)*tick)
    else:
        base = q.bid if (q.bid and q.bid > 0) else (q.last or q.close or 10.0)
        desired = base * (1.0 - slip_pct)
        px = max(desired, (q.bid - (ticks_clamp - 1) * tick) if (q.bid and q.bid > 0) else base - max(fallback_ticks,1)*tick)
    return round(round(px / tick) * tick, 10)

def spread_guard_ok(q: Quotes, cap_bps: float) -> Tuple[bool, Optional[float]]:
    bid, ask = q.bid, q.ask
    if not (bid and ask and bid > 0 and ask >= bid): return False, None
    mid = (bid + ask) / 2.0
    if mid <= 0: return False, None
    spread_bps = (ask - bid) / mid * 1e4
    return (spread_bps <= cap_bps), spread_bps

def now_et() -> datetime:
    return datetime.now(ZoneInfo("America/New_York")) if ZoneInfo else datetime.utcnow()

def rth_open_close(dt: Optional[datetime]=None):
    dt = dt or now_et()
    return dt.replace(hour=9, minute=30, second=0, microsecond=0), dt.replace(hour=16, minute=0, second=0, microsecond=0)

def is_rth_now(dt: Optional[datetime]=None) -> bool:
    dt = dt or now_et()
    if dt.weekday() >= 5: return False
    o,c = rth_open_close(dt)
    return o <= dt <= c

def minutes_since_open(dt: Optional[datetime]=None) -> Optional[int]:
    dt = dt or now_et()
    if not is_rth_now(dt): return None
    o,_ = rth_open_close(dt)
    return int((dt - o).total_seconds() // 60)

def dedupe_open_orders(ib: IB, symbol: str, side: str, mode: str="cancel_older"):
    side = side.upper()
    same = [t for t in ib.reqOpenOrders() if getattr(t.contract,"symbol",None)==symbol and t.order.action.upper()==side]
    if not same: return [], []
    key = lambda t: int(t.orderStatus.permId or t.order.permId or t.order.orderId or 0)
    same.sort(key=key)
    kept, cancelled = [], []
    if mode == "cancel_all_then_place":
        for t in same: ib.cancelOrder(t.order); cancelled.append(t)
    else:
        kept = [same[-1]]
        for t in same[:-1]: ib.cancelOrder(t.order); cancelled.append(t)
    ib.sleep(0.5); return kept, cancelled

def whatif_validate(ib: IB, contract: Contract, order: LimitOrder):
    trial = LimitOrder(order.action, order.totalQuantity, order.lmtPrice)
    trial.tif = order.tif; trial.outsideRth = getattr(order,"outsideRth",None)
    trial.algoStrategy = getattr(order,"algoStrategy",None)
    trial.algoParams  = getattr(order,"algoParams",None)
    trial.whatIf = True
    tr = ib.placeOrder(contract, trial); ib.sleep(0.6)
    err = None
    for log in tr.log:
        if getattr(log,"errorCode",0): err = f"{log.errorCode}: {log.message}"; break
    ok = tr.orderStatus.status in ("PreSubmitted","ApiPending","Submitted") and err is None
    return ok, err

def place_bracket(
    ib: IB,
    contract: Contract,
    side: str,
    qty: int,
    lmt: float,
    tp_pct: float,
    sl_pct: float,
    tif: str,
    outside_rth: bool,
    adaptive: Optional[str],  # None/"patient"/"normal"
    order_ref: str,
) -> Tuple[Trade, Trade, Trade]:
    side = side.upper(); assert side in ("BUY","SELL")
    parent_id = ib.client.getReqId(); tp_id = parent_id + 1; sl_id = parent_id + 2

    parent = LimitOrder(side, qty, lmt)
    parent.tif = tif
    parent.outsideRth = bool(outside_rth)
    parent.orderRef = order_ref
    parent.orderId = parent_id
    parent.transmit = False

    if adaptive:
        parent.algoStrategy = "Adaptive"
        prio = "Patient" if adaptive.lower().startswith("p") else "Normal"
        parent.algoParams = [TagValue("adaptivePriority", prio)]

    child_action = "SELL" if side == "BUY" else "BUY"
    tp_price = round(lmt * (1.0 + (tp_pct / 100.0) * (1 if side == "BUY" else -1)), 2)
    sl_price = round(lmt * (1.0 - (sl_pct / 100.0) * (1 if side == "BUY" else -1)), 2)

    take = LimitOrder(child_action, qty, tp_price)
    take.tif = tif
    take.parentId = parent_id
    take.ocaGroup = order_ref
    take.ocaType = 1
    take.transmit = False
    take.outsideRth = bool(outside_rth)     # <-- ensure TP is eligible outside RTH when needed
    take.orderRef = order_ref

    stop = StopOrder(child_action, qty, sl_price)
    stop.tif = tif
    stop.parentId = parent_id
    stop.ocaGroup = order_ref
    stop.ocaType = 1
    stop.transmit = True                    # last child transmits chain
    stop.outsideRth = bool(outside_rth)     # <-- ensure Stop is eligible outside RTH
    stop.orderRef = order_ref

    tr_parent = ib.placeOrder(contract, parent)
    tr_take   = ib.placeOrder(contract, take)
    tr_stop   = ib.placeOrder(contract, stop)
    ib.sleep(0.8)
    return tr_parent, tr_take, tr_stop

def run(host: str, port: int, client_id: int, symbol: str, side: str,
        qty: Optional[int], risk_cash: Optional[float], tif: str, outside_rth: bool,
        adaptive: Optional[str], orderref_prefix: str, slip_pct: float, ticks_clamp: int,
        fallback_ticks: int, spread_bps_cap: float, early_open_block_min: int,
        dedupe_mode: str, whatif: bool, autoreprice_sec: int, cooldown_min: int,
        tp_pct: float, sl_pct: float, slack_webhook: Optional[str]) -> None:

    if PAUSE_FLAG.exists():
        print("PAUSE flag present; aborting new orders."); return

    ib = IB(); ib.connect(host, port, clientId=client_id, timeout=30)
    contract = Stock(symbol, "SMART", "USD"); ib.qualifyContracts(contract)

    # Cooldown
    now_ts = int(time.time()); cooldowns: Dict[str,int] = {}
    if COOLDOWNS.exists():
        try: cooldowns = json.loads(COOLDOWNS.read_text("utf-8"))
        except Exception: cooldowns = {}
    key = symbol.upper(); until = cooldowns.get(key, 0)
    if until and now_ts < until:
        mins = int((until - now_ts)/60); print(f"Cooldown active for {symbol}: {mins} min left; aborting."); ib.disconnect(); return

    # Dedupe
    kept, cancelled = dedupe_open_orders(ib, symbol, side, mode=dedupe_mode)
    for t in cancelled:
        msg = {"event":"dedupe_cancel","symbol":t.contract.symbol,"action":t.order.action,
               "qty":float(t.order.totalQuantity),"permId":int(t.orderStatus.permId or t.order.orderId or 0)}
        print("Cancelled duplicate:", msg); _jsonl_write(JSONL_ORDERS, msg)

    # Session guards
    et = now_et()
    if not outside_rth and not is_rth_now(et):
        print("RTH-only and not in RTH; aborting (use --outside-rth 1 to override)."); ib.disconnect(); return
    mins = minutes_since_open(et)
    if mins is not None and mins < early_open_block_min:
        print(f"Early-open block: {mins} min since open < {early_open_block_min}; aborting."); ib.disconnect(); return

    # Quotes & clamps
    q = get_quotes(ib, contract)
    lmt = clamp_limit(side, q, slip_pct=slip_pct, ticks_clamp=ticks_clamp, fallback_ticks=fallback_ticks)

    ok, spread_bps = spread_guard_ok(q, spread_bps_cap)
    if spread_bps is not None and not ok:
        print(f"Spread too wide: {spread_bps:.2f} bps > cap {spread_bps_cap}; aborting."); ib.disconnect(); return

    # Sizing
    if qty is None:
        if not risk_cash: raise RuntimeError("--qty not given and --risk-cash not provided")
        stop_dist = lmt * (sl_pct/100.0)
        if stop_dist <= 0: raise RuntimeError("Invalid stop distance")
        qty = max(1, int(risk_cash // stop_dist))

    order_ref = f"{orderref_prefix}_{symbol}_{side}_{int(time.time())}"

    # What-if
    parent_probe = LimitOrder(side.upper(), qty, lmt); parent_probe.tif=tif; parent_probe.outsideRth=bool(outside_rth)
    if adaptive:
        parent_probe.algoStrategy="Adaptive"
        parent_probe.algoParams=[TagValue("adaptivePriority","Patient" if adaptive.lower().startswith("p") else "Normal")]
    if whatif:
        ok, err = whatif_validate(ib, contract, parent_probe)
        if not ok:
            print(f"What-if failed: {err}"); ib.disconnect(); return

    # Place bracket
    tr_parent, tr_take, tr_stop = place_bracket(ib, contract, side, qty, lmt, tp_pct, sl_pct, tif, outside_rth, adaptive, order_ref)

    placed = {"event":"placed","symbol":symbol,"side":side,"qty":qty,"lmt":lmt,"tp_pct":tp_pct,"sl_pct":sl_pct,
              "tif":tif,"outsideRth":outside_rth,"adaptive":adaptive,"orderRef":order_ref,
              "permId":int(tr_parent.orderStatus.permId or tr_parent.order.orderId or 0),
              "spread_bps":spread_bps,"quotes":{"bid":q.bid,"ask":q.ask,"last":q.last,"close":q.close,"minTick":q.minTick}}
    print("Placed:", placed); _jsonl_write(JSONL_ORDERS, placed)

    # Auto-reprice (once) if stale
    if autoreprice_sec > 0:
        deadline = time.time() + autoreprice_sec
        while time.time() < deadline:
            ib.waitOnUpdate(timeout=1.0)
            st = tr_parent.orderStatus.status
            if st not in ("PreSubmitted","Submitted"): break
        if tr_parent.orderStatus.status in ("PreSubmitted","Submitted"):
            print("Auto-reprice: canceling stale order and re-placing onceâ€¦")
            ib.cancelOrder(tr_parent.order); ib.sleep(0.6)
            q2 = get_quotes(ib, contract)
            lmt2 = clamp_limit(side, q2, slip_pct=slip_pct, ticks_clamp=ticks_clamp, fallback_ticks=fallback_ticks)
            tr_parent2, tr_take2, tr_stop2 = place_bracket(ib, contract, side, qty, lmt2, tp_pct, sl_pct, tif, outside_rth, adaptive, order_ref + "_R1")
            placed2 = {**placed, "event":"replaced", "lmt":lmt2, "permId":int(tr_parent2.orderStatus.permId or tr_parent2.order.orderId or 0)}
            print("Replaced:", placed2); _jsonl_write(JSONL_ORDERS, placed2)

    # Cooldown
    COOLDOWNS.write_text(json.dumps({**({} if not COOLDOWNS.exists() else json.loads(COOLDOWNS.read_text("utf-8") or "{}")),
                                     symbol.upper(): int(time.time() + cooldown_min*60)}, ensure_ascii=False), encoding="utf-8")

    # Snapshot
    oo = [{"permId": int(t.orderStatus.permId or t.order.orderId or 0),
           "symbol": t.contract.symbol, "action": t.order.action, "qty": float(t.order.totalQuantity),
           "status": t.orderStatus.status, "lmt": getattr(t.order,"lmtPrice",None),
           "tif": t.order.tif, "outsideRth": getattr(t.order,"outsideRth",None), "orderRef": t.order.orderRef}
          for t in ib.reqOpenOrders()]
    print("openOrders:", oo)
    ib.disconnect()

def build_parser():
    p = argparse.ArgumentParser(description="Protective LIMIT + Adaptive + Bracket OCO with guards")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=7497)
    p.add_argument("--client-id", type=int, default=2001)
    p.add_argument("--symbol", required=True)
    p.add_argument("--side", required=True, choices=["BUY","SELL","buy","sell"])
    sz = p.add_mutually_exclusive_group(required=False)
    sz.add_argument("--qty", type=int)
    sz.add_argument("--risk-cash", type=float)
    p.add_argument("--tif", default="DAY", choices=["DAY","GTC"])
    p.add_argument("--outside-rth", type=int, default=0)
    p.add_argument("--adaptive", choices=["patient","normal"], default=None)
    p.add_argument("--orderref-prefix", default="HATP_SMART")
    p.add_argument("--tp-pct", type=float, default=0.8)
    p.add_argument("--sl-pct", type=float, default=0.5)
    p.add_argument("--slip-pct", type=float, default=0.001)
    p.add_argument("--ticks-clamp", type=int, default=20)
    p.add_argument("--fallback-ticks", type=int, default=1)
    p.add_argument("--spread-bps-cap", type=float, default=8.0)
    p.add_argument("--early-open-block-min", type=int, default=2)
    p.add_argument("--dedupe-mode", choices=["cancel_older","cancel_all_then_place"], default="cancel_older")
    p.add_argument("--whatif", type=int, default=1)
    p.add_argument("--autoreprice-sec", type=int, default=0)
    p.add_argument("--cooldown-min", type=int, default=10)
    p.add_argument("--slack-webhook", default=os.environ.get("SLACK_WEBHOOK_URL"))
    return p

def main(argv: Optional[list[str]] = None) -> None:
    a = build_parser().parse_args(argv)
    run(host=a.host, port=a.port, client_id=a.client_id, symbol=a.symbol, side=a.side,
        qty=a.qty, risk_cash=a.risk_cash, tif=a.tif, outside_rth=bool(a.outside_rth),
        adaptive=a.adaptive, orderref_prefix=a.orderref_prefix, slip_pct=float(a.slip_pct),
        ticks_clamp=int(a.ticks_clamp), fallback_ticks=int(a.fallback_ticks),
        spread_bps_cap=float(a.spread_bps_cap), early_open_block_min=int(a.early_open_block_min),
        dedupe_mode=a.dedupe_mode, whatif=bool(a.whatif), autoreprice_sec=int(a.autoreprice_sec),
        cooldown_min=int(a.cooldown_min), tp_pct=float(a.tp_pct), sl_pct=float(a.sl_pct),
        slack_webhook=a.slack_webhook)

if __name__ == "__main__":
    main()

# --- override: place_bracket with StopLimit and OOH children ---
def place_bracket(ib, contract, side, qty, lmt, tp_pct, sl_pct, tif, outside_rth, adaptive, order_ref):
    side = (side or "").upper()
    assert side in ("BUY","SELL")
    parent_id = ib.client.getReqId()
    tp_id     = parent_id + 1
    sl_id     = parent_id + 2

    # Parent
    parent = LimitOrder(side, int(qty), float(lmt))
    parent.tif = tif
    parent.outsideRth = bool(outside_rth)
    parent.orderRef = order_ref
    parent.orderId = parent_id
    parent.transmit = False

    # Optional Adaptive (RTH only; caller should not set when outsideRth=True)
    if adaptive:
        parent.algoStrategy = "Adaptive"
        prio = "Patient" if str(adaptive).lower().startswith("p") else "Normal"
        parent.algoParams = [TagValue("adaptivePriority", prio)]

    # Children: TP LMT + STOP as StopLimit
    child_action = "SELL" if side == "BUY" else "BUY"
    tp_price = round(lmt * (1.0 + (tp_pct/100.0) * (1 if side=="BUY" else -1)), 2)
    sl_price = round(lmt * (1.0 - (sl_pct/100.0) * (1 if side=="BUY" else -1)), 2)

    # minTick for StopLimit offset
    cds = ib.reqContractDetails(contract)
    mt  = (cds[0].minTick or 0.01) if cds else 0.01
    off = 2 * mt  # 2 ticks through the stop

    # Take-profit (LMT)
    take = LimitOrder(child_action, int(qty), float(tp_price))
    take.tif = tif
    take.parentId = parent_id
    take.ocaGroup = order_ref
    take.ocaType  = 1
    take.transmit = False
    take.outsideRth = bool(outside_rth)
    take.orderRef   = order_ref

    # Stop-Limit child
    sl_lmt = round(sl_price - off, 2) if child_action=="SELL" else round(sl_price + off, 2)
    stop = StopLimitOrder(child_action, int(qty), float(sl_price), float(sl_lmt))
    stop.tif = tif
    stop.parentId = parent_id
    stop.ocaGroup = order_ref
    stop.ocaType  = 1
    stop.transmit = True
    stop.outsideRth = bool(outside_rth)
    stop.orderRef   = order_ref

    tr_parent = ib.placeOrder(contract, parent)
    tr_take   = ib.placeOrder(contract, take)
    tr_stop   = ib.placeOrder(contract, stop)
    ib.sleep(0.8)
    return tr_parent, tr_take, tr_stop

