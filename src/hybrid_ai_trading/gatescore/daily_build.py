from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict

from hybrid_ai_trading.gatescore.io import read_csv_rows
from hybrid_ai_trading.gatescore.quality import GateScoreThresholds, evaluate_thresholds


def _int(x: Any) -> int:
    try:
        return int(float(x))
    except Exception:
        return 0


def _float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0


def main() -> int:
    ap = argparse.ArgumentParser("gatescore.daily_build")
    ap.add_argument("-Symbol", "--Symbol", dest="symbol", default=os.environ.get("HAT_SYMBOL", "NVDA"))
    ap.add_argument("--csv", default=os.path.join("logs", "gatescore_daily_summary.csv"))
    ap.add_argument("--min-signals", type=int, default=100)
    ap.add_argument("--min-pnl-samples", type=int, default=300)
    ap.add_argument("--min-edge", type=float, default=0.03)
    ap.add_argument("--min-micro", type=float, default=0.55)
    args = ap.parse_args()

    sym = str(args.symbol).upper().strip()
    rows = read_csv_rows(args.csv)

    # Latest row for symbol (best-effort)
    row: Dict[str, Any] | None = None
    for r in rows:
        if str(r.get("symbol", "")).upper() == sym:
            row = r

    if row is None:
        out = {"symbol": sym, "as_of_date": "", "ok_today": False, "reason": "no_rows"}
        print(f"[gatescore.daily_build] {out}")
        return 2

    ok, reason = evaluate_thresholds(
        count_signals=_int(row.get("count_signals", 0)),
        pnl_samples=_int(row.get("pnl_samples", 0)),
        mean_edge_ratio=_float(row.get("mean_edge_ratio", 0.0)),
        mean_micro_score=_float(row.get("mean_micro_score", 0.0)),
        thr=GateScoreThresholds(int(args.min_signals), int(args.min_pnl_samples), float(args.min_edge), float(args.min_micro)),
    )

    out = {
        "symbol": sym,
        "as_of_date": str(row.get("as_of_date", ""))[:10],
        "ok_today": bool(ok),
        "reason": reason if ok else reason,
    }
    print(f"[gatescore.daily_build] {out}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
