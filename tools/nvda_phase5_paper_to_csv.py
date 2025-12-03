from __future__ import annotations

"""
Convert NVDA Phase-5 live-paper JSONL to CSV for Notion.

- Reads ALL JSON objects from logs/nvda_phase5_paperlive_results.jsonl,
  even if multiple JSON objects end up on one physical line.
- Writes a flat CSV with EV diagnostics + ORB+VWAP model EV
  for inspection and tuning in Notion.
"""

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(".").resolve()
SRC_JSONL = ROOT / "logs" / "nvda_phase5_paperlive_results.jsonl"
OUT_CSV   = ROOT / "logs" / "nvda_phase5_paper_for_notion.csv"


FIELDS: List[str] = [
    "ts",
    "symbol",
    "regime",
    "side",
    "price",
    "realized_pnl_paper",
    "ev",
    "phase5_allowed",
    "phase5_reason",
    # soft EV diagnostics
    "soft_ev_veto",
    "soft_ev_reason",
    "ev_band_abs",
    "ev_gap_abs",
    "ev_hit_flag",
    "ev_vs_realized_paper",
    "ev_band_veto_applied",
    "ev_band_veto_reason",
    # hard EV veto suggestion (log-only)
    "ev_hard_veto",
    "ev_hard_veto_reason",
    "ev_hard_veto_gap_abs",
    "ev_hard_veto_gap_threshold",
    # ORB+VWAP model EV (log-only)
    "ev_orb_vwap_model",
    "ev_effective_orb_vwap",
]


def read_all_json_objects(path: Path) -> List[Dict[str, Any]]:
    """
    Robust JSONL reader:

    - Treats the whole file as text.
    - Uses a regex to find every {...} JSON object.
    - Tries json.loads on each match, ignoring bad fragments.

    This avoids issues where multiple JSON objects accidentally
    land on the same physical line or have stray characters.
    """
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    rows: List[Dict[str, Any]] = []

    for match in re.finditer(r"\{.*?\}", text, flags=re.DOTALL):
        fragment = match.group(0).strip()
        if not fragment:
            continue
        try:
            obj = json.loads(fragment)
        except json.JSONDecodeError:
            continue
        rows.append(obj)

    return rows


def main() -> None:
    rows = read_all_json_objects(SRC_JSONL)
    if not rows:
        print(f"[NVDA-CSV] No JSON objects found in {SRC_JSONL}")
        return

    # Optionally filter to rows that look like NVDA Phase-5 diagnostic entries
    # (have symbol + realized_pnl_paper); this keeps the CSV focused.
    filtered: List[Dict[str, Any]] = []
    for r in rows:
        symbol = str(r.get("symbol", "")).upper()
        if symbol != "NVDA":
            continue
        if "realized_pnl_paper" not in r:
            continue
        filtered.append(r)

    if not filtered:
        print(f"[NVDA-CSV] No NVDA rows with realized_pnl_paper found in {SRC_JSONL}")
        return

    print(f"[NVDA-CSV] Writing {len(filtered)} rows to {OUT_CSV}")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for r in filtered:
            out: Dict[str, Any] = {}
            for field in FIELDS:
                out[field] = r.get(field)
            writer.writerow(out)


if __name__ == "__main__":
    main()