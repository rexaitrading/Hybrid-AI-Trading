from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

from hybrid_ai_trading.execution.gatescore_daily import load_daily_summary_for_symbol  # if exists
from hybrid_ai_trading.gatescore.quality import evaluate_row  # if exists

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]

def main(symbol: str) -> int:
    sym = symbol.strip().upper()
    today = date.today().isoformat()
    logs = _repo_root() / "logs"

    # Prefer per-symbol daily summary if present
    p1 = logs / f"gatescore_daily_summary_{sym.lower()}.csv"
    p2 = logs / "gatescore_daily_summary.csv"

    path = p1 if p1.exists() else p2
    if not path.exists():
        print(f"[GS-SMOKE] FAIL: missing daily summary csv: {path}")
        return 10

    # Minimal CSV parse (no pandas)
    import csv
    rows = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            rows.append(r)

    # Pick today's REAL row for symbol
    picked = None
    for r in rows:
        d = (r.get("as_of_date") or "")[:10]
        src = (r.get("source") or "").strip().upper()
        rsym = (r.get("symbol") or "").strip().upper()
        if d == today and src == "REAL" and (rsym == "" or rsym == sym):
            picked = r

    if not picked:
        print(f"[GS-SMOKE] FAIL: no REAL row for {sym} today={today}")
        return 10

    # Evaluate thresholds using existing psd1 thresholds logic mirrored in your PS builder:
    # count_signals>=3 (smoke), pnl_samples>=?; edge>=? micro>=?
    try:
        count_signals = int(float(picked.get("count_signals") or 0))
        pnl_samples = int(float(picked.get("pnl_samples") or 0))
        edge = float(picked.get("mean_edge_ratio") or 0.0)
        micro = float(picked.get("mean_micro_score") or 0.0)
    except Exception:
        print("[GS-SMOKE] FAIL: parse error")
        return 10

    print("[GS-SMOKE] PICK", sym, "signals", count_signals, "pnl", pnl_samples, "edge", edge, "micro", micro)

    # Hard smoke minimum (matches your existing NVDA smoke behavior you showed)
    if count_signals < 3:
        print("[GS-SMOKE] FAIL: count_signals < 3 (insufficient signal history).")
        return 10

    print("[GS-SMOKE] PASS")
    return 0

if __name__ == "__main__":
    import sys
    sym = "NVDA"
    if len(sys.argv) > 1:
        sym = sys.argv[1]
    raise SystemExit(main(sym))