from __future__ import annotations
import csv
import os
from datetime import datetime
from typing import Dict, List, Tuple
from bisect import bisect_right
from .replay_snapshots import render_symbol_snapshot

def parse_iso(ts: str) -> datetime:
    # Accept "YYYY-MM-DDTHH:MM:SS" or "...Z"
    t = (ts or "").strip()
    if not t:
        raise ValueError("empty ts")
    if t.endswith("Z"):
        t = t[:-1]
    try:
        return datetime.fromisoformat(t)
    except Exception:
        # fallback to strict format used by replay_journal.csv
        return datetime.strptime(t, "%Y-%m-%dT%H:%M:%S")

def load_series(path: str) -> Tuple[List[datetime], List[Dict]]:
    rows: List[Dict] = []
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            ts = row.get("ts")
            if not ts:
                continue
            try:
                row["_ts"] = parse_iso(ts)
            except Exception:
                continue
            # normalize numeric fields if present (optional)
            for k in ("open","high","low","close"):
                if k in row and row[k] is not None and row[k] != "":
                    try:
                        row[k] = float(row[k])
                    except Exception:
                        pass
            rows.append(row)
    rows.sort(key=lambda d: d["_ts"])
    times = [d["_ts"] for d in rows]
    return times, rows

def build_symbol_series(data_dir: str) -> Dict[str, Tuple[List[datetime], List[Dict]]]:
    series: Dict[str, Tuple[List[datetime], List[Dict]]] = {}
    for name in os.listdir(data_dir):
        if not name.lower().endswith(".csv"):
            continue
        sym = os.path.splitext(name)[0]
        t, r = load_series(os.path.join(data_dir, name))
        if t:
            series[sym] = (t, r)
    return series

def window_for_index(times: List[datetime], idx: int, lookback: int) -> Tuple[int, int]:
    if not times:
        return (0, 0)
    lo = max(0, idx - max(1, lookback) + 1)
    hi = idx + 1
    return (lo, hi)

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--journal-csv", required=True)
    ap.add_argument("--out-csv", default="logs/replay_journal.snap.csv")
    ap.add_argument("--snapshots-dir", required=True)
    ap.add_argument("--window", type=int, default=60, help="bars per snapshot window")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out_csv) or ".", exist_ok=True)
    os.makedirs(args.snapshots_dir, exist_ok=True)

    series = build_symbol_series(args.data_dir)

    with open(args.journal_csv, newline="", encoding="utf-8") as fi, \
         open(args.out_csv, "w", newline="", encoding="utf-8") as fo:

        r = csv.DictReader(fi)
        fieldnames = list(r.fieldnames or [])
        if "screenshot_path" not in fieldnames:
            fieldnames.append("screenshot_path")
        w = csv.DictWriter(fo, fieldnames=fieldnames)
        w.writeheader()

        for row in r:
            sym = (row.get("symbol") or "").strip()
            ts_str = (row.get("ts") or row.get("time") or "").strip()
            if not sym or not ts_str or sym not in series:
                row["screenshot_path"] = ""
                w.writerow(row)
                continue

            try:
                t = parse_iso(ts_str)
            except Exception:
                row["screenshot_path"] = ""
                w.writerow(row)
                continue

            times, rows = series[sym]
            k = bisect_right(times, t) - 1
            if k < 0:
                row["screenshot_path"] = ""
                w.writerow(row)
                continue

            lo, hi = window_for_index(times, k, args.window)
            hist = rows[lo:hi]
            out_name = f"{sym}_{t.strftime('%Y%m%d_%H%M%S')}.png"
            out_path = os.path.join(args.snapshots_dir, sym, out_name)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            shot = render_symbol_snapshot(sym, hist, out_path)
            row["screenshot_path"] = shot or ""
            w.writerow(row)

    print(f"[snap] wrote {args.out_csv}")

if __name__ == "__main__":
    main()