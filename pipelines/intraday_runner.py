from __future__ import annotations
import os, sys, json, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path: sys.path.insert(0, ROOT)

from typing import List, Dict, Any, Tuple
from utils.ib_preview import whatif_preview
from utils.position_sizer import compute_size
from risk.daily_targeting import compute_risk_cap
from risk.guardrails import guardrails
from risk.kill_switch import init_baseline, should_halt
from signals.simple_signals import signal_score
from utils.slack_notify import notify

LOG_TRADES = os.path.join("logs", "trades.jsonl"); os.makedirs("logs", exist_ok=True)

def _parse_hm(s: str, default: Tuple[str,str]) -> Tuple[str,str]:
    try:
        hh, mm = s.split(":"); hh_i, mm_i = int(hh), int(mm)
        if 0 <= hh_i < 24 and 0 <= mm_i < 60: return (f"{hh_i:02d}", f"{mm_i:02d}")
    except Exception:
        pass
    return default

def run_once(symbols: List[str],
             kelly: float = 0.7,
             allocation: float = 0.5,
             daily_target: float = 0.007,
             margin_frac_limit: float = 0.20,
             safety_buffer_pct: float = 0.02,
             max_qty: int = 20,
             start_hm: Tuple[str,str] = ("06","00"),
             end_hm: Tuple[str,str] = ("11","00"),
             min_score: float = 0.55,
             max_trades: int = 3,
             twap_min_qty: int = 8,
             twap_slices: int = 3,
             twap_gap: float = 0.5,
             dry_run: bool = True,
             loss_cap_frac: float = 0.01):
    results = []

    # 0) Baseline for kill-switch
    pv0 = whatif_preview(symbols[0], qty=1)
    netliq0 = pv0.get("equityWithLoan")
    init_baseline(netliq0 or 0.0, loss_cap_frac)

    # 1) Score & sort
    scored = []
    for sym in symbols:
        sc = signal_score(sym)
        pv1 = whatif_preview(sym, qty=1)
        mpu = pv1.get("initMargin_perUnit") or pv1.get("maintMargin_perUnit") or 1e9
        scored.append({"symbol": sym, "score": sc["score"], "mpu": mpu})
    scored.sort(key=lambda x: (-x["score"], x["mpu"]))

    # 2) Take top-K that pass min_score
    picked = [s for s in scored if s["score"] >= min_score][:max_trades]
    if not picked:
        notify("No symbols passed score filter")
        return results

    for row in picked:
        sym = row["symbol"]

        # check kill-switch
        pv_net = whatif_preview(sym, qty=1)
        netliq = pv_net.get("equityWithLoan")
        if should_halt(netliq or 0.0, loss_cap_frac):
            entry = {"symbol": sym, "halted": True, "reason": f"loss_cap {loss_cap_frac:.2%} breached", "netliq": netliq}
            results.append(entry)
            with open(LOG_TRADES, "a", encoding="utf-8") as f: f.write(json.dumps(entry)+"\n")
            notify(f"HALT: loss cap {loss_cap_frac:.2%} breached. NetLiq={netliq}")
            break

        # risk budget & sizing
        rc = compute_risk_cap(netliq_cad=float(netliq or 0.0), daily_target=daily_target, allocation=allocation)
        sz = compute_size(sym, risk_cap_cad=rc["risk_cap_cad"], kelly_fraction=kelly,
                          safety_buffer_pct=safety_buffer_pct, max_qty=max_qty)

        # final validation
        final_pv = whatif_preview(sym, qty=sz["qty"])
        ok, msg = guardrails({**final_pv}, max_margin_frac=margin_frac_limit, max_qty=max_qty,
                             start=start_hm, end=end_hm)
        entry = {"symbol": sym, "score": row["score"], "sizer": sz, "preview": final_pv, "guardrails": msg, "ok": ok}

        if ok and sz["qty"] > 0:
            if dry_run:
                entry["order"] = {"would_send": True, "qty": sz["qty"], "side": "BUY"}
                notify(f"DRY-RUN {sym} qty={sz['qty']} PASS")
            else:
                if sz["qty"] >= twap_min_qty:
                    from execution.twap import twap_market
                    send = twap_market(sym, total_qty=sz["qty"], slices=twap_slices, gap_sec=twap_gap)
                else:
                    from execution.paper_order import place_market
                    send = place_market(sym, sz["qty"], side="BUY")
                entry["order"] = send
                notify(f"SENT {sym} qty={sz['qty']}")
        else:
            entry["order"] = {"skipped": True}
            notify(f"SKIP {sym}: {msg}")

        results.append(entry)
        with open(LOG_TRADES, "a", encoding="utf-8") as f: f.write(json.dumps(entry)+"\n")
        time.sleep(0.4)
    return results

if __name__ == "__main__":
    syms = os.environ.get("QP_SYMBOLS", "AAPL").split(",")
    syms = [s.strip().upper() for s in syms if s.strip()]

    kelly = float(os.environ.get("QP_KELLY", "0.7"))
    allocation = float(os.environ.get("QP_ALLOCATION", "0.5"))
    daily_target = float(os.environ.get("QP_DAILY_TARGET", "0.007"))
    margin_frac_limit = float(os.environ.get("QP_MARGIN_LIMIT", "0.20"))
    safety_buffer_pct = float(os.environ.get("QP_SAFETY", "0.02"))
    max_qty = int(os.environ.get("QP_MAX_QTY", "20"))
    start_hm = (os.environ.get("QP_START","06:00")[:2], os.environ.get("QP_START","06:00")[3:5])
    end_hm   = (os.environ.get("QP_END","11:00")[:2],   os.environ.get("QP_END","11:00")[3:5])
    min_score = float(os.environ.get("QP_MIN_SCORE", "0.55"))
    max_trades = int(os.environ.get("QP_MAX_TRADES", "3"))
    twap_min_qty = int(os.environ.get("QP_TWAP_MIN_QTY", "8"))
    twap_slices = int(os.environ.get("QP_TWAP_SLICES", "3"))
    twap_gap = float(os.environ.get("QP_TWAP_GAP", "0.5"))
    dry_run = os.environ.get("QP_DRY_RUN","1") != "0"
    loss_cap_frac = float(os.environ.get("QP_LOSS_CAP", "0.010"))

    out = run_once(syms, kelly=kelly, allocation=allocation,
                   daily_target=daily_target, margin_frac_limit=margin_frac_limit,
                   safety_buffer_pct=safety_buffer_pct, max_qty=max_qty,
                   start_hm=start_hm, end_hm=end_hm, min_score=min_score,
                   max_trades=max_trades, twap_min_qty=twap_min_qty, twap_slices=twap_slices,
                   twap_gap=twap_gap, dry_run=dry_run, loss_cap_frac=loss_cap_frac)
    print(json.dumps(out, indent=2))