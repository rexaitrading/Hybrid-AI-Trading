"""
Phase-2 microstructure enrichment for SPY/QQQ Phase-5 ORB CSVs.

- Uses hybrid_ai_trading.microstructure.compute_microstructure_features
- Computes:
    - ms_range_pct   := abs(window_ret)
    - ms_trend_flag  := sign(last_ret) in { -1, 0, +1 }
- Enriches:
    - logs/spy_phase5_paper_for_notion_ev_diag.csv
    - logs/qqq_phase5_paper_for_notion_ev_diag.csv

Log-only: no gating changes, no config writes.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence

from hybrid_ai_trading.microstructure import compute_microstructure_features


def _float_or_default(val, default: float) -> float:
    try:
        if val is None:
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def enrich_file(path: Path) -> None:
    if not path.exists():
        print(f"[MICRO-ENRICH] SKIP: {path} not found.")
        return

    print(f"[MICRO-ENRICH] Loading {path} ...")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print(f"[MICRO-ENRICH] SKIP: {path} is empty.")
        return

    # Use 'price' as close proxy, and qty/qty_used as volume proxy.
    closes = [_float_or_default(r.get("price"), 0.0) for r in rows]
    volumes = [
        _float_or_default(
            r.get("qty_used", r.get("qty", 1.0)),
            1.0,
        )
        for r in rows
    ]

    features = compute_microstructure_features(closes=closes, volumes=volumes)

    window_ret = getattr(features, "window_ret", 0.0)
    last_ret = getattr(features, "last_ret", 0.0)

    ms_range_pct = abs(window_ret)

    if last_ret > 0:
        ms_trend_flag = 1
    elif last_ret < 0:
        ms_trend_flag = -1
    else:
        ms_trend_flag = 0

    print(
        "[MICRO-ENRICH] Derived features:"
        f" window_ret={window_ret:.6f}, last_ret={last_ret:.6f},"
        f" ms_range_pct={ms_range_pct:.6f}, ms_trend_flag={ms_trend_flag}"
    )

    fieldnames = list(rows[0].keys())
    for extra in ("ms_range_pct", "ms_trend_flag"):
        if extra not in fieldnames:
            fieldnames.append(extra)

    for r in rows:
        r["ms_range_pct"] = f"{ms_range_pct:.6f}"
        r["ms_trend_flag"] = ms_trend_flag

    out_path = path.with_name(path.stem + "_micro.csv")
    print(f"[MICRO-ENRICH] Writing enriched CSV to {out_path} ...")
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[MICRO-ENRICH] Done for {path} -> {out_path}")


def main() -> None:
    print("[MICRO-ENRICH] === SPY/QQQ microstructure enrichment start ===")
    base = Path("logs")
    spy = base / "spy_phase5_paper_for_notion_ev_diag.csv"
    qqq = base / "qqq_phase5_paper_for_notion_ev_diag.csv"

    enrich_file(spy)
    enrich_file(qqq)

    print("[MICRO-ENRICH] === SPY/QQQ microstructure enrichment complete ===")


if __name__ == "__main__":
    main()