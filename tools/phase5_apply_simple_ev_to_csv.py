"""
Apply simple EV overrides to Phase-5 CSVs.

- Reads config/phase5/ev_simple.json for regime -> EV mapping.
- For each Phase-5 live CSV:
    logs/nvda_phase5_paper_for_notion.csv
    logs/spy_phase5_paper_for_notion.csv
    logs/qqq_phase5_paper_for_notion.csv

  If a row has:
    side == "SELL"
    and ev is missing / empty / 0.0
  then we overwrite ev with the simple EV for that row's regime.

PnL columns are never changed.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, Any


EV_CONFIG_PATH = Path("config/phase5/ev_simple.json")

CSV_TARGETS = [
    Path("logs/nvda_phase5_paper_for_notion.csv"),
    Path("logs/spy_phase5_paper_for_notion.csv"),
    Path("logs/qqq_phase5_paper_for_notion.csv"),
]


def load_simple_ev_map(path: Path = EV_CONFIG_PATH) -> Dict[str, float]:
    if not path.exists():
        print(f"[EV] Config not found at {path}, no overrides will be applied.")
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        ev_map: Dict[str, float] = {}
        for k, v in data.items():
            try:
                ev_map[str(k)] = float(v)
            except (TypeError, ValueError):
                continue
        print(f"[EV] Loaded {len(ev_map)} regime EV values from {path}")
        return ev_map
    except Exception as e:
        print(f"[EV] Failed to load {path}: {e}")
        return {}


def try_parse_float(val: Any) -> float | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def patch_csv_ev(csv_path: Path, ev_map: Dict[str, float]) -> None:
    if not csv_path.exists():
        print(f"[CSV] {csv_path} not found, skipping.")
        return

    tmp_path = csv_path.with_suffix(csv_path.suffix + ".tmp")

    print(f"[CSV] Processing {csv_path} ...")

    with csv_path.open("r", encoding="utf-8", newline="") as rf:
        reader = csv.DictReader(rf)
        fieldnames = reader.fieldnames or []
        # Ensure 'ev' column exists
        if "ev" not in fieldnames:
            fieldnames.append("ev")

        rows_out = []
        patched_rows = 0

        for row in reader:
            side = (row.get("side") or "").strip().upper()
            regime = (row.get("regime") or "").strip()
            ev_raw = row.get("ev")

            current_ev = try_parse_float(ev_raw)
            simple_ev = ev_map.get(regime)

            if (
                side == "SELL"
                and simple_ev is not None
                and (current_ev is None or abs(current_ev) < 1e-12)
            ):
                row["ev"] = f"{simple_ev:.8f}"
                patched_rows += 1

            rows_out.append(row)

    with tmp_path.open("w", encoding="utf-8", newline="") as wf:
        writer = csv.DictWriter(wf, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    # Replace original file
    csv_path.unlink()
    tmp_path.rename(csv_path)

    print(f"[CSV] {csv_path}: patched {patched_rows} SELL rows with EV overrides.")


def main() -> None:
    ev_map = load_simple_ev_map()
    if not ev_map:
        print("[MAIN] No EV map loaded, nothing to do.")
        return

    for csv_path in CSV_TARGETS:
        patch_csv_ev(csv_path, ev_map)


if __name__ == "__main__":
    main()