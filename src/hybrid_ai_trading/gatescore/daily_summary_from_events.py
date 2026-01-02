from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

HEADER = ["as_of_date","symbol","count_signals","pnl_samples","mean_edge_ratio","mean_micro_score"]

def _float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0

def _int(x: Any) -> int:
    try:
        return int(float(x))
    except Exception:
        return 0

def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = (ln or "").strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out

def _events_paths(logs: Path) -> Dict[str, Path]:
    return {
        "NVDA": (logs / "nvda_gatescore_events.jsonl"),
        "NVDA_STUB": (logs / "nvda_gatescore_events_stub.jsonl"),
        "SPY": (logs / "spy_gatescore_events.jsonl"),
        "QQQ": (logs / "qqq_gatescore_events.jsonl"),
    }

def _pick_events(logs: Path, sym: str) -> Path:
    m = _events_paths(logs)
    if sym.upper() == "NVDA":
        if m["NVDA"].exists() and m["NVDA"].stat().st_size > 0:
            return m["NVDA"]
        return m["NVDA_STUB"]
    return m[sym.upper()]

def _aggregate(sym: str, events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    cnt_signals = 0
    pnl_samples = 0
    edges: List[float] = []
    micros: List[float] = []
    for e in events:
        cnt_signals += max(1, _int(e.get("count_signals", 1)))
        pnl_samples += max(0, _int(e.get("pnl_samples", 0)))
        if "edge_ratio" in e:
            edges.append(_float(e.get("edge_ratio", 0.0)))
        if "micro_score" in e:
            micros.append(_float(e.get("micro_score", 0.0)))
    mean_edge = sum(edges)/len(edges) if edges else 0.0
    mean_micro = sum(micros)/len(micros) if micros else 0.0
    return {
        "symbol": sym.upper(),
        "count_signals": cnt_signals,
        "pnl_samples": pnl_samples,
        "mean_edge_ratio": mean_edge,
        "mean_micro_score": mean_micro,
    }

def _read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        rdr = csv.DictReader(f)
        return [dict(r) for r in rdr]

def _write_csv_rows(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # UTF-8 no BOM, LF
    with path.open("w", encoding="utf-8", newline="\n") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in HEADER})

def main() -> int:
    ap = argparse.ArgumentParser("gatescore.daily_summary_from_events")
    ap.add_argument("--as-of-date", default=os.environ.get("HAT_ASOF_DATE","").strip())
    ap.add_argument("--csv", default=os.path.join("logs","gatescore_daily_summary.csv"))
    ap.add_argument("--logs", default="logs")
    args = ap.parse_args()

    as_of = (args.as_of_date or "").strip()
    if not as_of:
        # Fail-closed: require explicit session date (PowerShell drives HAT_ASOF_DATE).
        print(json.dumps({"ok": False, "reason": "missing_as_of_date"}, indent=2))
        return 2

    logs = Path(args.logs)
    csvp = Path(args.csv)

    # Load existing canonical rows
    rows = _read_csv_rows(csvp)

    # Remove any existing rows for as_of for NVDA/SPY/QQQ (upsert)
    keep: List[Dict[str, Any]] = []
    for r in rows:
        d = (r.get("as_of_date","") or "")[:10]
        s = (r.get("symbol","") or "").upper()
        if d == as_of and s in ("NVDA","SPY","QQQ"):
            continue
        keep.append(r)

    out_rows: List[Dict[str, Any]] = []
    out_rows.extend(keep)

    for sym in ("NVDA","SPY","QQQ"):
        p = _pick_events(logs, sym)
        ev = [e for e in _read_jsonl(p) if (str(e.get("as_of_date",""))[:10] == as_of and str(e.get("symbol","")).upper()==sym)]
        if not ev:
            # fail-closed: do not fabricate today rows
            continue
        agg = _aggregate(sym, ev)
        agg["as_of_date"] = as_of
        out_rows.append(agg)

    _write_csv_rows(csvp, out_rows)
    print(json.dumps({"as_of_date": as_of, "wrote": str(csvp), "rows": len(out_rows)}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())