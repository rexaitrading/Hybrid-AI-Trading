from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from datetime import date

ROOT = Path(__file__).resolve().parents[2]
LOGS = ROOT / "logs"

IN_JSONL = LOGS / "nvda_phase5_paperlive_results.jsonl"
OUT_CSV  = LOGS / "gatescore_daily_summary.csv"

HEADER = "as_of_date,symbol,count_signals,pnl_samples,mean_edge_ratio,mean_micro_score"


def main() -> int:
    today = date.today().isoformat()

    if not IN_JSONL.exists():
        print("[GATESCORE] Missing input JSONL – fail-closed")
        return 0

    rows = []
    with IN_JSONL.open("r", encoding="utf-8-sig") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                rows.append(json.loads(ln))
            except Exception:
                continue

    # Filter to today + NVDA only
    rows = [
        r for r in rows
        if str(r.get("symbol","")).upper() == "NVDA"
        and str(r.get("ts_trade",""))[:10] == today
    ]

    if not rows:
        print("[GATESCORE] No rows for today – fail-closed")
        return 0

    realized = [r.get("realized_pnl", 0.0) for r in rows]
    edges    = [r.get("edge_ratio", 0.0) for r in rows if "edge_ratio" in r]
    micros   = [r.get("micro_score", 0.0) for r in rows if "micro_score" in r]

    count_signals = len(rows)
    pnl_samples   = len(realized)

    mean_edge  = mean(edges)  if edges  else 0.0
    mean_micro = mean(micros) if micros else 0.0

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    rewrite = True
    if OUT_CSV.exists():
        try:
            first = OUT_CSV.read_text(encoding="ascii").splitlines()[0]
            if first.strip() == HEADER:
                rewrite = False
        except Exception:
            rewrite = True

    if rewrite:
        OUT_CSV.write_text(HEADER + "\n", encoding="ascii")

    with OUT_CSV.open("a", encoding="ascii") as f:
        f.write(
            f"{today},NVDA,{count_signals},{pnl_samples},{mean_edge:.6f},{mean_micro:.6f}\n"
        )

    print(
        f"[GATESCORE] today={today} "
        f"signals={count_signals} pnl_samples={pnl_samples} "
        f"mean_edge={mean_edge:.4f} mean_micro={mean_micro:.4f}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())