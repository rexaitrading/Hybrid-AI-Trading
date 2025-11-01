from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

# ib_insync
from ib_insync import IB, Contract, LimitOrder, Stock, StopLimitOrder, TagValue, Trade

# ---------- paths / audit ----------
ROOT = Path.cwd()
LOGS = ROOT / "logs"
STATE = ROOT / "state"
CONTROL = ROOT / "control"
for d in (LOGS, STATE, CONTROL):
    d.mkdir(parents=True, exist_ok=True)
JSONL_ORDERS = LOGS / "orders.jsonl"
COOLDOWNS = STATE / "cooldowns.json"
PAUSE_FLAG = CONTROL / "PAUSE"


def _jsonl(obj: Dict) -> None:
    with JSONL_ORDERS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


# ---------- quotes / clamp ----------
@dataclass
class Quotes:
    bid: Optional[float]
    ask: Optional[float]
    last: Optional[float]
    close: Optional[float]
    minTick: float


def _min_tick(ib: IB, contract: Contract) -> float:
    cds = ib.reqContractDetails(contract)
    if not cds:
        raise RuntimeError("No contract details")
    return float(cds[0].minTick or 0.01)


def get_quotes(ib: IB, contract: Contract) -> Quotes:
    mt = _min_tick(ib, contract)
    tk = ib.reqMktData(contract, "", False, False)
    ib.sleep(1.2)
    bid = getattr(tk, "bid", None)
    ask = getattr(tk, "ask", None)
    last = getattr(tk, "last", None)
    close = getattr(tk, "close", None)
    if (not last) and hasattr(tk, "marketPrice"):
        try:
            mp = tk.marketPrice()
            if mp and mp > 0:
                last = mp
        except Exception:
            pass
    return Quotes(bid, ask, last, close, mt)


def clamp_limit(
    side: str, q: Quotes, slip_pct: float, ticks_clamp: int, fallback_ticks: int
) -> float:
    side = side.upper()
    tick = max(q.minTick, 0.01)
    if side == "BUY":
        base = q.ask if (q.ask and q.ask > 0) else (q.last or q.close or 10.0)
        desired = base * (1.0 + slip_pct)
        # -1 tick safety to avoid Error 382
        px = (
            min(desired, (q.ask + (ticks_clamp - 1) * tick))
            if (q.ask and q.ask > 0)
            else base + max(fallback_ticks, 1) * tick
        )
    else:
        base = q.bid if (q.bid and q.bid > 0) else (q.last or q.close or 10.0)
        desired = base * (1.0 - slip_pct)
        px = (
            max(desired, (q.bid - (ticks_clamp - 1) * tick))
            if (q.bid and q.bid > 0)
            else base - max(fallback_ticks, 1) * tick
        )
    return round(round(px / tick) * tick, 10)


def spread_guard_ok(q: Quotes, cap_bps: float) -> Tuple[bool, Optional[float]]:
    b, a = q.bid, q.ask
    if not (b and a and b > 0 and a >= b):
        return False, None
    mid = (b + a) / 2.0
    if mid <= 0:
        return False, None
    spr = a - b
    bps = (spr / mid) * 1e4
    return (bps <= cap_bps), bps


# ---------- dedupe / what-if ----------
def dedupe_open_orders(
    ib: IB, symbol: str, side: str, mode: str = "cancel_older"
) -> Tuple[list[Trade], list[Trade]]:
    side = side.upper()
    same = [
        t
        for t in ib.reqOpenOrders()
        if getattr(t.contract, "symbol", None) == symbol
        and t.order.action.upper() == side
    ]
    if not same:
        return [], []
    key = lambda t: int(t.orderStatus.permId or t.order.permId or t.order.orderId or 0)
    same.sort(key=key)
    kept, cancelled = [], []
    if mode == "cancel_all_then_place":
        for t in same:
            ib.cancelOrder(t.order)
            cancelled.append(t)
    else:
        kept = [same[-1]]
        for t in same[:-1]:
            ib.cancelOrder(t.order)
            cancelled.append(t)
    ib.sleep(0.5)
    return kept, cancelled


def whatif_validate(
    ib: IB, contract: Contract, order: LimitOrder
) -> Tuple[bool, Optional[str]]:
    trial = LimitOrder(order.action, order.totalQuantity, order.lmtPrice)
    trial.tif = order.tif
    trial.outsideRth = getattr(order, "outsideRth", None)
    trial.algoStrategy = getattr(order, "algoStrategy", None)
    trial.algoParams = getattr(order, "algoParams", None)
    trial.whatIf = True
    tr = ib.placeOrder(contract, trial)
    ib.sleep(0.6)
    err = None
    for log in tr.log:
        if getattr(log, "errorCode", 0):
            err = f"{log.errorCode}: {log.message}"
            break
    ok = (
        tr.orderStatus.status in ("PreSubmitted", "ApiPending", "Submitted")
        and err is None
    )
    return ok, err


# ---------- bracket builder (TP=LMT, STOP=StopLimit with OOH children) ----------
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
    adaptive: Optional[str],
    order_ref: str,
) -> Tuple[Trade, Trade, Trade]:
    side = side.upper()
    assert side in ("BUY", "SELL")
    parent_id = ib.client.getReqId()
    tp_id = parent_id + 1
    sl_id = parent_id + 2

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

    cds = ib.reqContractDetails(contract)
    mt = (cds[0].minTick or 0.01) if cds else 0.01
    off = 2 * mt  # 2 ticks through the stop

    take = LimitOrder(child_action, qty, tp_price)
    take.tif = tif
    take.parentId = parent_id
    take.ocaGroup = order_ref
    take.ocaType = 1
    take.transmit = False
    take.outsideRth = bool(outside_rth)
    take.orderRef = order_ref

    sl_lmt = (
        round(sl_price - off, 2) if child_action == "SELL" else round(sl_price + off, 2)
    )
    stop = StopLimitOrder(child_action, qty, sl_price, sl_lmt)
    stop.tif = tif
    stop.parentId = parent_id
    stop.ocaGroup = order_ref
    stop.ocaType = 1
    stop.transmit = True
    stop.outsideRth = bool(outside_rth)
    stop.orderRef = order_ref

    tr_parent = ib.placeOrder(contract, parent)
    tr_take = ib.placeOrder(contract, take)
    tr_stop = ib.placeOrder(contract, stop)
    ib.sleep(0.8)
    return tr_parent, tr_take, tr_stop


# ---------- run / cli ----------
def run(
    host: str,
    port: int,
    client_id: int,
    symbol: str,
    side: str,
    qty: Optional[int],
    risk_cash: Optional[float],
    tif: str,
    outside_rth: bool,
    adaptive: Optional[str],
    orderref_prefix: str,
    slip_pct: float,
    ticks_clamp: int,
    fallback_ticks: int,
    spread_bps_cap: float,
    early_open_block_min: int,
    dedupe_mode: str,
    whatif: bool,
    autoreprice_sec: int,
    cooldown_min: int,
    tp_pct: float,
    sl_pct: float,
    slack_webhook: Optional[str],
) -> None:
    if PAUSE_FLAG.exists():
        print("PAUSE present; abort.")
        return

    ib = IB()
    ib.connect(host, port, clientId=client_id, timeout=30)
    contract = Stock(symbol, "SMART", "USD")
    ib.qualifyContracts(contract)

    # Cooldown
    now_ts = int(time.time())
    cooldowns: Dict[str, int] = {}
    if COOLDOWNS.exists():
        try:
            cooldowns = json.loads(COOLDOWNS.read_text("utf-8") or "{}")
        except Exception:
            cooldowns = {}
    key = symbol.upper()
    if cooldowns.get(key, 0) > now_ts:
        mins = (cooldowns[key] - now_ts) // 60
        print(f"Cooldown active for {symbol}: {mins} min left; abort.")
        ib.disconnect()
        return

    # Dedupe
    kept, cancelled = dedupe_open_orders(ib, symbol, side, mode=dedupe_mode)
    for t in cancelled:
        _jsonl(
            {
                "event": "dedupe_cancel",
                "symbol": t.contract.symbol,
                "action": t.order.action,
                "qty": float(t.order.totalQuantity),
                "permId": int(t.orderStatus.permId or t.order.orderId or 0),
            }
        )

    # Quotes / spread / clamp
    q = get_quotes(ib, contract)
    ok, spr_bps = spread_guard_ok(q, spread_bps_cap)
    if (spr_bps is not None) and (not ok):
        print(f"Spread too wide: {spr_bps:.2f} bps > cap {spread_bps_cap}; abort.")
        ib.disconnect()
        return
    lmt = clamp_limit(
        side,
        q,
        slip_pct=slip_pct,
        ticks_clamp=ticks_clamp,
        fallback_ticks=fallback_ticks,
    )

    # Sizing
    if qty is None:
        if not risk_cash:
            raise RuntimeError("--qty not given and --risk-cash missing")
        stop_dist = lmt * (sl_pct / 100.0)
        if stop_dist <= 0:
            raise RuntimeError("Invalid stop distance")
        qty = max(1, int(risk_cash // stop_dist))

    order_ref = f"{orderref_prefix}_{symbol}_{side}_{int(time.time())}"

    # What-if (ON in RTH use-cases, OFF outside RTH via runner flags)
    parent_probe = LimitOrder(side.upper(), qty, lmt)
    parent_probe.tif = tif
    parent_probe.outsideRth = bool(outside_rth)
    if adaptive:
        parent_probe.algoStrategy = "Adaptive"
        prio = "Patient" if adaptive.lower().startswith("p") else "Normal"
        parent_probe.algoParams = [TagValue("adaptivePriority", prio)]
    if whatif:
        ok, err = whatif_validate(ib, contract, parent_probe)
        if not ok:
            print(f"What-if failed: {err}")
            ib.disconnect()
            return

    # Place bracket
    tr_parent, tr_take, tr_stop = place_bracket(
        ib,
        contract,
        side,
        qty,
        lmt,
        tp_pct,
        sl_pct,
        tif,
        outside_rth,
        adaptive,
        order_ref,
    )
    placed = {
        "event": "placed",
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "lmt": lmt,
        "tp_pct": tp_pct,
        "sl_pct": sl_pct,
        "tif": tif,
        "outsideRth": outside_rth,
        "adaptive": adaptive,
        "orderRef": order_ref,
        "permId": int(tr_parent.orderStatus.permId or tr_parent.order.orderId or 0),
        "spread_bps": spr_bps,
        "quotes": {
            "bid": q.bid,
            "ask": q.ask,
            "last": q.last,
            "close": q.close,
            "minTick": q.minTick,
        },
    }
    print("Placed:", placed)
    _jsonl(placed)

    # Auto-reprice once if stuck
    if autoreprice_sec > 0:
        deadline = time.time() + autoreprice_sec
        while time.time() < deadline and tr_parent.orderStatus.status in (
            "PreSubmitted",
            "Submitted",
        ):
            ib.waitOnUpdate(timeout=1.0)
        if tr_parent.orderStatus.status in ("PreSubmitted", "Submitted"):
            print("Auto-reprice: canceling stale order and re-placing onceâ€¦")
            ib.cancelOrder(tr_parent.order)
            ib.sleep(0.6)
            q2 = get_quotes(ib, contract)
            lmt2 = clamp_limit(
                side,
                q2,
                slip_pct=slip_pct,
                ticks_clamp=ticks_clamp,
                fallback_ticks=fallback_ticks,
            )
            tr_parent2, tr_take2, tr_stop2 = place_bracket(
                ib,
                contract,
                side,
                qty,
                lmt2,
                tp_pct,
                sl_pct,
                tif,
                outside_rth,
                adaptive,
                order_ref + "_R1",
            )
            placed2 = {
                **placed,
                "event": "replaced",
                "lmt": lmt2,
                "permId": int(
                    tr_parent2.orderStatus.permId or tr_parent2.order.orderId or 0
                ),
            }
            print("Replaced:", placed2)
            _jsonl(placed2)

    # Cooldown update
    cooldowns[key] = int(time.time() + cooldown_min * 60)
    COOLDOWNS.write_text(json.dumps(cooldowns), encoding="utf-8")

    # Snapshot
    oo = [
        {
            "permId": int(t.orderStatus.permId or t.order.orderId),
            "symbol": t.contract.symbol,
            "action": t.order.action,
            "qty": float(t.order.totalQuantity),
            "status": t.orderStatus.status,
            "lmt": getattr(t.order, "lmtPrice", None),
            "tif": t.order.tif,
            "outsideRth": getattr(t.order, "outsideRth", None),
            "orderRef": t.order.orderRef,
        }
        for t in ib.reqOpenOrders()
    ]
    print("openOrders:", oo)
    ib.disconnect()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Protective LIMIT + Adaptive + Bracket OCO with guards"
    )
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=7497)
    p.add_argument("--client-id", type=int, default=2001)
    p.add_argument("--symbol", required=True)
    p.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"])
    g = p.add_mutually_exclusive_group(required=False)
    g.add_argument("--qty", type=int)
    g.add_argument("--risk-cash", type=float)
    p.add_argument("--tif", default="DAY", choices=["DAY", "GTC"])
    p.add_argument("--outside-rth", type=int, default=0)
    p.add_argument("--adaptive", choices=["patient", "normal"], default=None)
    p.add_argument("--orderref-prefix", default="HATP_SMART")
    p.add_argument("--tp-pct", type=float, default=0.8)
    p.add_argument("--sl-pct", type=float, default=0.5)
    p.add_argument("--slip-pct", type=float, default=0.001)
    p.add_argument("--ticks-clamp", type=int, default=20)
    p.add_argument("--fallback-ticks", type=int, default=1)
    p.add_argument("--spread-bps-cap", type=float, default=8.0)
    p.add_argument("--early-open-block-min", type=int, default=2)
    p.add_argument(
        "--dedupe-mode",
        choices=["cancel_older", "cancel_all_then_place"],
        default="cancel_older",
    )
    p.add_argument("--whatif", type=int, default=1)
    p.add_argument("--autoreprice-sec", type=int, default=0)
    p.add_argument("--cooldown-min", type=int, default=10)
    p.add_argument("--slack-webhook", default=os.environ.get("SLACK_WEBHOOK_URL"))
    return p


def main(argv: Optional[list[str]] = None) -> None:
    a = build_parser().parse_args(argv)
    run(
        host=a.host,
        port=a.port,
        client_id=a.client_id,
        symbol=a.symbol,
        side=a.side,
        qty=a.qty,
        risk_cash=a.risk_cash,
        tif=a.tif,
        outside_rth=bool(a.outside_rth),
        adaptive=a.adaptive,
        orderref_prefix=a.orderref_prefix,
        slip_pct=float(a.slip_pct),
        ticks_clamp=int(a.ticks_clamp),
        fallback_ticks=int(a.fallback_ticks),
        spread_bps_cap=float(a.spread_bps_cap),
        early_open_block_min=int(a.early_open_block_min),
        dedupe_mode=a.dedupe_mode,
        whatif=bool(a.whatif),
        autoreprice_sec=int(a.autoreprice_sec),
        cooldown_min=int(a.cooldown_min),
        tp_pct=float(a.tp_pct),
        sl_pct=float(a.sl_pct),
        slack_webhook=a.slack_webhook,
    )


if __name__ == "__main__":
    main()
