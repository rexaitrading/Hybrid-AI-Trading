from __future__ import annotations

from datetime import date
from pathlib import Path
import csv

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]

def _pick_row(rows: list[dict], sym: str, today: str) -> dict | None:
    symu = sym.upper()
    picked = None
    for r in rows:
        d = (r.get("as_of_date") or "")[:10]
        src = (r.get("source") or "").strip().upper()
        rsym = (r.get("symbol") or "").strip().upper()
        if d != today:
            continue
        if src != "REAL":
            continue
        if rsym and rsym != symu:
            continue
        picked = r
    return picked

def main(sym: str) -> int:
    sym = sym.strip().upper()
    today = date.today().isoformat()
    logs = _repo_root() / "logs"

    p1 = logs / f"gatescore_daily_summary_{sym.lower()}.csv"
    p2 = logs / "gatescore_daily_summary.csv"
    path = p1 if p1.exists() else p2

    if not path.exists():
        print(f"[GS-SMOKE] FAIL: missing daily summary csv: {path}")
        return 10

    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        rd = csv.DictReader(f)
        rows = list(rd)

    row = _pick_row(rows, sym, today)
    if not row:
        print(f"[GS-SMOKE] FAIL: no REAL row for {sym} today={today}")
        return 10

    try:
        count_signals = int(float(row.get("count_signals") or 0))
        pnl_samples = int(float(row.get("pnl_samples") or 0))
        edge = float(row.get("mean_edge_ratio") or 0.0)
        micro = float(row.get("mean_micro_score") or 0.0)
    except Exception:
        print("[GS-SMOKE] FAIL: parse error")
        return 10

    print(f"[GS-SMOKE] {sym} GateScore health snapshot:")
    print("  symbol          =", sym)
    print("  count_signals   =", count_signals)
    print("  pnl_samples     =", pnl_samples)
    print("  mean_edge_ratio =", f"{edge:.6f}")
    print("  mean_micro_score=", f"{micro:.6f}")

    if count_signals < 3:
        print("[GS-SMOKE] FAIL: count_signals < 3 (insufficient signal history).")
        return 10

    print("[GS-SMOKE] PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main("SPY"))