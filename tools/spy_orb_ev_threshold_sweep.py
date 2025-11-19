from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List, Optional


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser("SPY ORB/VWAP EV vs GateScore edge_ratio threshold sweep")
    ap.add_argument(
        "--jsonl",
        default=os.path.join("research", "spy_orb_vwap_replay_trades_enriched.jsonl"),
        help="Input enriched JSONL (default: research/spy_orb_vwap_replay_trades_enriched.jsonl)",
    )
    ap.add_argument(
        "--start",
        type=float,
        default=0.00,
        help="Start threshold for edge_ratio sweep (default: 0.00)",
    )
    ap.add_argument(
        "--stop",
        type=float,
        default=0.10,
        help="Stop threshold for edge_ratio sweep (inclusive, default: 0.10)",
    )
    ap.add_argument(
        "--step",
        type=float,
        default=0.01,
        help="Step for edge_ratio sweep (default: 0.01)",
    )
    ap.add_argument(
        "--min-pnl-pct",
        type=float,
        default=-1.0,
        help="Minimum pnl_pct filter (default: -1.0 = no filter)",
    )
    ap.add_argument(
        "--max-cost-bp",
        type=float,
        default=9999.0,
        help="Maximum cost_bp filter (default: 9999.0 = no filter)",
    )
    return ap.parse_args(argv)


def load_trades(jsonl_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(jsonl_path):
        raise FileNotFoundError(f"JSONL not found: {jsonl_path}")
    trades: List[Dict[str, Any]] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                trades.append(rec)
            except Exception as exc:
                print(f"[SPY-THR] ERROR parsing line: {exc}")
    return trades


def safe_float(rec: Dict[str, Any], key: str, default: float = 0.0) -> float:
    v = rec.get(key, default)
    try:
        return float(v)
    except Exception:
        return default


def sweep(trades: List[Dict[str, Any]], start: float, stop: float, step: float, min_pnl_pct: float, max_cost_bp: float) -> None:
    if not trades:
        print("[SPY-THR] No trades to analyze.")
        return

    print("[SPY-THR] Total trades:", len(trades))
    print("[SPY-THR] Sweep edge_ratio from", start, "to", stop, "step", step)
    print("[SPY-THR] Filters: min_pnl_pct>=", min_pnl_pct, "max_cost_bp<=", max_cost_bp)
    print()
    print(f"{'thresh':>7} {'count':>6} {'mean_pnl_pct':>13} {'mean_ev':>10} {'mean_cost_bp':>13}")

    thr = start
    while thr <= stop + 1e-9:
        selected: List[Dict[str, Any]] = []
        for rec in trades:
            er = safe_float(rec, "gatescore_edge_ratio", 0.0)
            pnl_pct = safe_float(rec, "pnl_pct", 0.0)
            cost_bp = safe_float(rec, "cost_bp", 0.0)
            if er < thr:
                continue
            if pnl_pct < min_pnl_pct:
                continue
            if cost_bp > max_cost_bp:
                continue
            selected.append(rec)

        if not selected:
            print(f"{thr:7.3f} {0:6d} {0.0:13.6f} {0.0:10.6f} {0.0:13.6f}")
        else:
            n = len(selected)
            sum_pnl = 0.0
            sum_ev = 0.0
            sum_cost = 0.0
            for rec in selected:
                pnl_pct = safe_float(rec, 'pnl_pct', 0.0)
                ev = safe_float(rec, 'ev', 0.0)
                cost_bp = safe_float(rec, 'cost_bp', 0.0)
                sum_pnl += pnl_pct
                sum_ev += ev
                sum_cost += cost_bp
            mean_pnl = sum_pnl / n
            mean_ev = sum_ev / n
            mean_cost = sum_cost / n
            print(f"{thr:7.3f} {n:6d} {mean_pnl:13.6f} {mean_ev:10.6f} {mean_cost:13.6f}")

        thr += step


def main() -> None:
    args = parse_args()
    trades = load_trades(args.jsonl)
    sweep(
        trades=trades,
        start=args.start,
        stop=args.stop,
        step=args.step,
        min_pnl_pct=args.min_pnl_pct,
        max_cost_bp=args.max_cost_bp,
    )


if __name__ == "__main__":
    main()