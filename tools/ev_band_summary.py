from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Dict


def summarize(path: str, label: str) -> None:
    """
    Print simple counts of ev_band_reason values for a given CSV.
    """
    counts: Counter[str] = Counter()
    csv_path = Path(path)

    if not csv_path.exists():
        print(f"[WARN] {label}: file not found at {csv_path}")
        return

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            reason = (row.get("ev_band_reason") or "").strip() or "missing"
            counts[reason] += 1

    print(f"\n== {label} ==")
    if not counts:
        print("  (no rows)")
        return

    for key, value in sorted(counts.items()):
        print(f"  {key:15s} {value:3d}")


def main() -> None:
    configs: Dict[str, str] = {
        "NVDA_BPLUS_LIVE": "logs/nvda_phase5_paperlive_with_ev_band.csv",
        "SPY_ORB_LIVE": "logs/spy_phase5_paperlive_with_ev_band.csv",
        "QQQ_ORB_LIVE": "logs/qqq_phase5_paperlive_with_ev_band.csv",
    }

    for label, path in configs.items():
        summarize(path, label)


if __name__ == "__main__":
    main()