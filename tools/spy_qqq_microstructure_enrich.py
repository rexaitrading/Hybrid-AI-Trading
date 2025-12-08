"""
Phase-2 microstructure enrichment for SPY/QQQ Phase-5 ORB CSVs.

This version makes ms_range_pct and ms_trend_flag explicitly
ORB-window based:

- ms_range_pct  := abs(orb_ret)
    orb_ret = (last_close - first_close) / first_close

- ms_trend_flag := sign(orb_ret) in { -1, 0, +1 }

Input (as before):
    logs/spy_phase5_paper_for_notion_ev_diag.csv
    logs/qqq_phase5_paper_for_notion_ev_diag.csv

Output:
    logs/spy_phase5_paper_for_notion_ev_diag_micro.csv
    logs/qqq_phase5_paper_for_notion_ev_diag_micro.csv

Log-only diagnostics. No gating or risk behaviour changes.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List


def _float_or_default(val, default: float) -> float:
    try:
        if val is None:
            return default
        if val == "":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def compute_orb_window_features(closes: List[float]) -> tuple[float, int]:
    """
    Compute a simple ORB-window return based microstructure pair:

    - ms_range_pct  = abs(orb_ret)
    - ms_trend_flag = sign(orb_ret) in { -1, 0, +1 }

    where orb_ret = (last_close - first_close) / first_close
    """
    if not closes:
        return 0.0, 0

    first = closes[0]
    last = closes[-1]

    if first == 0:
        return 0.0, 0

    orb_ret = (last - first) / first

    if orb_ret > 0:
        trend_flag = 1
    elif orb_ret < 0:
        trend_flag = -1
    else:
        trend_flag = 0

    ms_range_pct = abs(orb_ret)
    return ms_range_pct, trend_flag


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

    # Use 'price' as a close proxy.
    closes = [_float_or_default(r.get("price"), 0.0) for r in rows]

    # ORB-window features based on first/last price
    ms_range_pct, ms_trend_flag = compute_orb_window_features(closes)

    print(
        "[MICRO-ENRICH] ORB-window features:"
        f" first_close={closes[0]:.6f} last_close={closes[-1]:.6f} "
        f"ms_range_pct={ms_range_pct:.6f} ms_trend_flag={ms_trend_flag}"
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
    print("[MICRO-ENRICH] === SPY/QQQ microstructure enrichment (ORB-window) start ===")
    base = Path("logs")
    spy = base / "spy_phase5_paper_for_notion_ev_diag.csv"
    qqq = base / "qqq_phase5_paper_for_notion_ev_diag.csv"

    enrich_file(spy)
    enrich_file(qqq)

    print("[MICRO-ENRICH] === SPY/QQQ microstructure enrichment (ORB-window) complete ===")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Phase-2 microstructure enrichment for SPY/QQQ Phase-5 ORB CSVs."
    )
    parser.add_argument(
        "--symbol",
        choices=["SPY", "QQQ", "BOTH"],
        default="BOTH",
        help="Which symbol(s) to process. Default: BOTH."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="If set, only print what would be done without writing files."
    )
    args = parser.parse_args()

    # Assume script lives under tools/, repo root is two levels up
    repo_root = Path(__file__).resolve().parents[2]
    logs_dir = repo_root / "logs"

    targets = []
    if args.symbol in ("SPY", "BOTH"):
        targets.append(logs_dir / "spy_phase5_paper_for_notion_ev_diag.csv")
    if args.symbol in ("QQQ", "BOTH"):
        targets.append(logs_dir / "qqq_phase5_paper_for_notion_ev_diag.csv")

    print("[MICRO-ENRICH] === SPY/QQQ microstructure enrichment (ORB-window) start ===")
    for src in targets:
        rel = src.relative_to(repo_root)
        print(f"[MICRO-ENRICH] Target: {rel}")
        if args.dry_run:
            if not src.exists():
                print(f"[MICRO-ENRICH] DRY RUN: {rel} not found.")
            else:
                print(f"[MICRO-ENRICH] DRY RUN: would enrich {rel}")
            continue
        enrich_file(src)
    print("[MICRO-ENRICH] === SPY/QQQ microstructure enrichment (ORB-window) complete ===")
