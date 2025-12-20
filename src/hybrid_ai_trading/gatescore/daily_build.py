from __future__ import annotations

import argparse
from pathlib import Path

from .io import read_daily_csv
from .quality import GateScoreThresholds, evaluate_thresholds


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="logs/gatescore_daily_summary.csv")
    ap.add_argument("--symbol", default="NVDA")
    ap.add_argument("--min-signals", type=int, default=100)
    ap.add_argument("--min-pnl-samples", type=int, default=300)
    ap.add_argument("--min-edge", type=float, default=0.03)
    ap.add_argument("--min-micro", type=float, default=0.55)
    args = ap.parse_args()

    rows = read_daily_csv(args.csv)
    sym = args.symbol.upper()
    today = None
    for r in rows:
        if r.symbol == sym:
            today = r  # last match wins
    if today is None:
        print("[gatescore.daily_build] FAIL: no row for symbol", sym)
        return 2

    ok, reason = evaluate_thresholds(
        count_signals=today.count_signals,
        pnl_samples=today.pnl_samples,
        mean_edge_ratio=today.mean_edge_ratio,
        mean_micro_score=today.mean_micro_score,
        thr=GateScoreThresholds(args.min_signals, args.min_pnl_samples, args.min_edge, args.min_micro),
    )
    print("[gatescore.daily_build]", {"symbol": sym, "as_of_date": today.as_of_date, "ok_today": ok, "reason": reason})
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())