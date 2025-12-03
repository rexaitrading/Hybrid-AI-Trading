from __future__ import annotations

"""
Quick EV research helper for Block-E.

Reads the NVDA/SPY/QQQ Phase-5 CSVs used by Notion and prints, for each symbol:

- total_rows: all rows in the CSV (excluding header)
- bandA_rows: rows with ev_band_abs == 1
- bandA_soft_veto: rows in Band A where soft_ev_veto is true
- bandA_avg_ev: average EV in Band A
- bandA_avg_model: average ev_orb_vwap_model in Band A
- bandA_avg_effective: average ev_effective_orb_vwap in Band A
"""

import csv
import math
from pathlib import Path
from typing import Dict, List, Iterable, Optional


ROOT = Path(".").resolve()


def _safe_float(value: object) -> float:
    """
    Convert a CSV cell to float, returning NaN if it is missing or invalid.
    """
    if value is None:
        return math.nan
    text = str(value).strip()
    if not text:
        return math.nan
    try:
        return float(text)
    except (TypeError, ValueError):
        return math.nan


def _mean(values: Iterable[float]) -> float:
    """
    Simple mean that ignores NaN values.
    """
    clean: List[float] = [v for v in values if not math.isnan(v)]
    if not clean:
        return math.nan
    return sum(clean) / len(clean)


def summarize_csv(path: Path, label: str) -> None:
    if not path.exists():
        print(f"=== {label} ===")
        print(f"CSV not found: {path}")
        print()
        return

    rows: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Require symbol just to avoid blank lines
            symbol = (row.get("symbol") or "").strip().upper()
            if not symbol:
                continue
            rows.append(row)

    total_rows = len(rows)

    band_a_rows: List[Dict[str, str]] = []
    for row in rows:
        band_val = row.get("ev_band_abs")
        band_str = (str(band_val) if band_val is not None else "").strip()
        if band_str in ("1", "1.0"):
            band_a_rows.append(row)

    def _is_soft_veto(row: Dict[str, str]) -> bool:
        v = row.get("soft_ev_veto")
        if v is None:
            return False
        text = str(v).strip().lower()
        return text in ("true", "1", "yes", "y", "checked")

    band_a_soft_veto = [r for r in band_a_rows if _is_soft_veto(r)]

    avg_ev = _mean(_safe_float(r.get("ev")) for r in band_a_rows)
    avg_model = _mean(_safe_float(r.get("ev_orb_vwap_model")) for r in band_a_rows)
    avg_effective = _mean(_safe_float(r.get("ev_effective_orb_vwap")) for r in band_a_rows)

    print(f"=== {label} ===")
    print(f"total_rows={total_rows}, bandA_rows={len(band_a_rows)}, bandA_soft_veto={len(band_a_soft_veto)}")

    if math.isnan(avg_ev):
        print("bandA_avg_ev=NA")
    else:
        print(f"bandA_avg_ev={avg_ev:.4f}")

    if math.isnan(avg_model):
        print("bandA_avg_model=NA")
    else:
        print(f"bandA_avg_model={avg_model:.4f}")

    if math.isnan(avg_effective):
        print("bandA_avg_effective=NA")
    else:
        print(f"bandA_avg_effective={avg_effective:.4f}")

    print()


def main() -> None:
    summarize_csv(
        ROOT / "logs" / "nvda_phase5_paper_for_notion.csv",
        label="NVDA_BPLUS_LIVE",
    )
    summarize_csv(
        ROOT / "logs" / "spy_phase5_paper_for_notion.csv",
        label="SPY_ORB_LIVE",
    )
    summarize_csv(
        ROOT / "logs" / "qqq_phase5_paper_for_notion.csv",
        label="QQQ_ORB_LIVE",
    )


if __name__ == "__main__":
    main()