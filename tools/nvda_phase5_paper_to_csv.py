"""
Convert NVDA Phase-5 paper-live JSONL -> CSV for Notion.

Input : logs/nvda_phase5_paperlive_results.jsonl
Output: logs/nvda_phase5_paper_for_notion.csv

Assumption: 1 JSON object per line.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(".").resolve()
SRC_JSONL = ROOT / "logs" / "nvda_phase5_paperlive_results.jsonl"
OUT_CSV  = ROOT / "logs" / "nvda_phase5_paper_for_notion.csv"


FIELDS: List[str] = [
    "ts",
    "entry_ts",
    "symbol",
    "regime",
    "side",
    "qty",
    "price",
    "realized_pnl",
    "phase5_allowed",
    "phase5_reason",
    "soft_ev_veto",
    "soft_ev_reason",
    "ev_band_abs",
    "ev_gap_abs",
    "ev_hit_flag",
    "ev_band_veto_applied",
    "ev_band_veto_reason",
    "ev_hard_veto",
    "ev_hard_veto_reason",
    "ev_hard_veto_gap_abs",
    "ev_hard_veto_gap_threshold",
    "ev_orb_vwap_model",
    "ev_effective_orb_vwap",
]


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
        except Exception:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _get(d: Dict[str, Any], k: str, default: Any = "") -> Any:
    v = d.get(k, default)
    return default if v is None else v


def main() -> None:
    rows = _read_jsonl(SRC_JSONL)
    if not rows:
        print(f"[NVDA-CSV] No JSON objects found in {SRC_JSONL}")
        # Still write header-only CSV (stable for Notion import)
        with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
        return

    out_rows: List[Dict[str, Any]] = []
    for r in rows:
        pr = r.get("phase5_result") or {}
        if not isinstance(pr, dict):
            pr = {}

        out = {k: "" for k in FIELDS}
        out["ts"]        = _get(r, "ts", "")
        out["entry_ts"]  = _get(r, "entry_ts", _get(r, "ts", ""))
        out["symbol"]    = _get(r, "symbol", "NVDA")
        out["regime"]    = _get(r, "regime", "")
        out["side"]      = _get(r, "side", "")
        out["qty"]       = _get(r, "qty", "")
        out["price"]     = _get(r, "price", "")
        out["realized_pnl"] = _get(r, "realized_pnl", 0.0)

        # Phase-5 decision fields (runner may store flat or nested)
        out["phase5_allowed"] = pr.get("allowed", r.get("phase5_allowed", ""))
        out["phase5_reason"]  = pr.get("reason",  r.get("phase5_reason", ""))

        # EV-band / veto fields (best-effort)
        for k in [
            "soft_ev_veto","soft_ev_reason","ev_band_abs","ev_gap_abs","ev_hit_flag",
            "ev_band_veto_applied","ev_band_veto_reason",
            "ev_hard_veto","ev_hard_veto_reason","ev_hard_veto_gap_abs","ev_hard_veto_gap_threshold",
            "ev_orb_vwap_model","ev_effective_orb_vwap",
        ]:
            out[k] = r.get(k, "")

        out_rows.append(out)

    print(f"[NVDA-CSV] Writing {len(out_rows)} rows to {OUT_CSV}")
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out_rows)


if __name__ == "__main__":
    main()