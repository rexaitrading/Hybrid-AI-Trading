from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser("AAPL ORB/VWAP EV report from gated enriched JSONL")
    ap.add_argument(
        "--jsonl",
        default=os.path.join("research", "aapl_orb_vwap_replay_trades_gated.jsonl"),
        help="Gated enriched JSONL path (default: research/aapl_orb_vwap_replay_trades_gated.jsonl)",
    )
    return ap.parse_args(argv)


def _load_trades(jsonl_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(jsonl_path):
        raise FileNotFoundError(f"JSONL not found: {jsonl_path}")
    trades: List[Dict[str, Any]] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                trades.append(rec)
            except Exception as exc:
                print(f"[AAPL-GATED-REPORT] ERROR parsing line {line_no}: {exc}")
    return trades


def _safe_float(d: Dict[str, Any], key: str, default: float = 0.0) -> float:
    v = d.get(key, default)
    try:
        return float(v)
    except Exception:
        return default


def make_report(trades: List[Dict[str, Any]]) -> None:
    if not trades:
        print("[AAPL-GATED-REPORT] No trades found in gated JSONL.")
        return

    n = len(trades)
    sum_pnl = 0.0
    sum_ev = 0.0
    sum_cost_bp = 0.0

    for rec in trades:
        pnl_pct = _safe_float(rec, "pnl_pct", 0.0)
        ev = _safe_float(rec, "ev", 0.0)
        cost_bp = _safe_float(rec, "cost_bp", 0.0)
        sum_pnl += pnl_pct
        sum_ev += ev
        sum_cost_bp += cost_bp

    mean_pnl = sum_pnl / n
    mean_ev = sum_ev / n
    mean_cost_bp = sum_cost_bp / n

    print("[AAPL-GATED-REPORT] Gated AAPL ORB/VWAP EV summary")
    print("  trades:", n)
    print(f"  mean_pnl_pct: {mean_pnl:.6f}")
    print(f"  mean_ev:      {mean_ev:.6f}")
    print(f"  mean_cost_bp: {mean_cost_bp:.3f}")


def main() -> None:
    args = parse_args()
    trades = _load_trades(args.jsonl)
    print(f"[AAPL-GATED-REPORT] Loaded {len(trades)} gated trade(s) from {args.jsonl}")
    make_report(trades)


if __name__ == "__main__":
    main()