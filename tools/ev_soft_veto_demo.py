from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Dict

from hybrid_ai_trading.risk.risk_phase5_ev_soft_veto import (
    phase5_ev_soft_veto_from_flags,
)


def summarize_soft_veto(csv_path: Path, label: str) -> None:
    if not csv_path.exists():
        print(f"[EV-SOFT-DEMO] {label}: file not found at {csv_path}")
        return

    counts: Counter[str] = Counter()

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            flags = {
                "ev_band_allowed": _parse_bool(row.get("ev_band_allowed")),
                "ev_band_reason": (row.get("ev_band_reason") or "").strip() or None,
                "ev_band_veto_applied": _parse_bool(row.get("ev_band_veto_applied")),
                "ev_band_veto_reason": (row.get("ev_band_veto_reason") or "").strip() or None,
                "locked_by_ev_band": _parse_bool(row.get("locked_by_ev_band")),
            }
            soft = phase5_ev_soft_veto_from_flags(flags)
            key = "soft_veto" if soft["soft_ev_veto"] else "soft_allow"
            reason = soft["soft_ev_reason"] or "none"
            counts[(key, reason)] += 1

    print(f"\n== Soft EV veto summary :: {label} ==")
    if not counts:
        print("  (no rows)")
        return

    for (key, reason), value in sorted(counts.items()):
        print(f"  {key:10s} reason={reason:15s} count={value:3d}")


def _parse_bool(val: str | None) -> bool:
    if val is None:
        return False
    v = str(val).strip().lower()
    return v in ("1", "true", "yes", "y", "checked")


def main() -> None:
    configs: Dict[str, str] = {
        "NVDA_BPLUS_LIVE": "logs/nvda_phase5_paperlive_with_ev_band.csv",
        "SPY_ORB_LIVE": "logs/spy_phase5_paperlive_with_ev_band.csv",
        "QQQ_ORB_LIVE": "logs/qqq_phase5_paperlive_with_ev_band.csv",
    }
    for label, rel in configs.items():
        summarize_soft_veto(Path(rel), label)


if __name__ == "__main__":
    main()