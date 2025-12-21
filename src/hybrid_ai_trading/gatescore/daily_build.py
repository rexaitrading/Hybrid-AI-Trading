# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

EPS = 1e-12


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    raw = path.read_text(encoding="utf-8-sig").splitlines()
    if not raw or len(raw) < 2:
        raise RuntimeError(f"CSV empty/too small: {path}")
    # DictReader handles quoted headers/values fine
    reader = csv.DictReader(raw)
    return [dict(r) for r in reader if r]


def _pick_latest_row(rows: list[dict[str, str]], symbol: str) -> dict[str, str]:
    sym = symbol.upper().strip()
    # Filter by symbol if column exists
    if rows and "symbol" in {k.lower() for k in rows[0].keys()}:
        # Find actual casing of 'symbol'
        sym_key = next((k for k in rows[0].keys() if k.lower() == "symbol"), "symbol")
        cand = [r for r in rows if (r.get(sym_key, "") or "").upper().strip() == sym]
        if cand:
            rows = cand

    # Prefer max as_of_date if present
    if rows and any(k.lower() == "as_of_date" for k in rows[0].keys()):
        date_key = next((k for k in rows[0].keys() if k.lower() == "as_of_date"), "as_of_date")
        rows_sorted = sorted(rows, key=lambda r: (r.get(date_key, "") or ""))
        return rows_sorted[-1]

    return rows[-1]


def _f(x: Any) -> Optional[float]:
    if x is None:
        return None
    s = str(x).strip().strip('"')
    if s == "":
        return None
    try:
        return float(s)
    except Exception:
        return None


def _i(x: Any) -> Optional[int]:
    v = _f(x)
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        return None


def _infer_csv_from_status(status_path: Path) -> Optional[Path]:
    d = status_path.resolve().parent
    cands = [
        d / "gatescore_pnl_summary.csv",
        d / "gatescore_daily_summary.csv",
        d / "gatescore_daily_summary_nvda.csv",
    ]
    for c in cands:
        if c.exists():
            return c
    return None


def main() -> None:
    ap = argparse.ArgumentParser("GateScore daily_build")
    ap.add_argument("--csv", help="Input CSV for daily_build (preferred).", default=None)
    ap.add_argument("--symbol", default="NVDA")
    ap.add_argument("--min-signals", type=int, default=100)
    ap.add_argument("--min-pnl-samples", type=int, default=300)
    ap.add_argument("--min-edge", type=float, default=0.03)
    ap.add_argument("--min-micro", type=float, default=0.55)

    # --- Backward-compatible optional flags (Phase3 PS glue / ops convenience) ---
    ap.add_argument(
        "--status-path",
        default=None,
        help="(compat) Path to Block-G status JSON. If --csv not provided, infer CSV near this path.",
    )
    ap.add_argument(
        "--out",
        default=None,
        help="(compat) Write a single JSON line result to this path (JSONL).",
    )

    args = ap.parse_args()

    csv_path: Optional[Path] = Path(args.csv) if args.csv else None

    if csv_path is None and args.status_path:
        stp = Path(args.status_path)
        if stp.exists():
            csv_path = _infer_csv_from_status(stp)

    if csv_path is None:
        raise SystemExit("daily_build: missing --csv (and could not infer from --status-path)")

    if not csv_path.exists():
        raise SystemExit(f"daily_build: csv not found: {csv_path}")

    rows = _read_csv_rows(csv_path)
    row = _pick_latest_row(rows, args.symbol)

    # Column normalization (handles quoted keys)
    keys = {k.lower(): k for k in row.keys()}

    asof = (row.get(keys.get("as_of_date", "as_of_date"), "") or "").strip().strip('"')
    sym = (row.get(keys.get("symbol", "symbol"), args.symbol) or "").strip().strip('"') or args.symbol

    count_signals = _i(row.get(keys.get("count_signals", "count_signals")))
    pnl_samples = _i(row.get(keys.get("pnl_samples", "pnl_samples")))
    mean_edge = _f(row.get(keys.get("mean_edge_ratio", "mean_edge_ratio")))
    mean_micro = _f(row.get(keys.get("mean_micro_score", "mean_micro_score")))

    reasons = []
    ok = True

    if count_signals is None or count_signals < int(args.min_signals):
        ok = False
        reasons.append(f"min_signals:{count_signals}<{args.min_signals}")
    if pnl_samples is None or pnl_samples < int(args.min_pnl_samples):
        ok = False
        reasons.append(f"min_pnl_samples:{pnl_samples}<{args.min_pnl_samples}")
    if mean_edge is None or (float(mean_edge) + EPS) < float(args.min_edge):
        ok = False
        reasons.append(f"min_edge:{mean_edge}<{args.min_edge}")
    if mean_micro is None or (float(mean_micro) + EPS) < float(args.min_micro):
        ok = False
        reasons.append(f"min_micro:{mean_micro}<{args.min_micro}")

    reason = "ok" if ok else ";".join(reasons)

    out: Dict[str, Any] = {
        "symbol": str(sym).upper(),
        "as_of_date": asof,
        "ok_today": bool(ok),
        "reason": reason,
    }

    print("[gatescore.daily_build]", out)

    # compat: write JSONL output if requested
    if args.out:
        op = Path(args.out)
        op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text(json.dumps(out, separators=(",", ":")) + "\n", encoding="utf-8")

    # Contract: 0 ok, 2 not-ready
    raise SystemExit(0 if ok else 2)


if __name__ == "__main__":
    main()