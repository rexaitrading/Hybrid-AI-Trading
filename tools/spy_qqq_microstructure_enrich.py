from __future__ import annotations

import csv
from pathlib import Path


def main() -> int:
    """
    Phase-2 microstructure enrichment stub for SPY/QQQ.

    v0 behaviour:
      - Locate logs/spy_qqq_micro_for_notion.csv if present.
      - Print a small sample to stdout.
      - Exit 0 regardless (best-effort, does not gate anything).

    This is intentionally light: the real microstructure + cost model logic
    lives in Build-Phase2CostFromTicks.ps1 and related tools. This script
    simply gives Run-Phase2ToPhase5Validation.ps1 a safe target to call.
    """
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[1]
    logs_dir = repo_root / "logs"
    csv_path = logs_dir / "spy_qqq_micro_for_notion.csv"

    if not csv_path.exists():
        print("[MICRO-ENRICH] SKIP: spy_qqq_micro_for_notion.csv not found (nothing to enrich).")
        return 0

    # Avoid printing the full Windows path (may contain non-ASCII -> encoding issues).
    print("[MICRO-ENRICH] Found microstructure CSV; showing sample rows...")
    try:
        with csv_path.open(newline="") as f:
            reader = csv.DictReader(f)
            rows = []
            for i, row in enumerate(reader):
                if i >= 10:
                    break
                rows.append(row)
    except Exception as e:
        print(f"[MICRO-ENRICH] ERROR reading spy_qqq_micro_for_notion.csv: {e!r}")
        return 0

    if not rows:
        print("[MICRO-ENRICH] No data rows found in spy_qqq_micro_for_notion.csv")
        return 0

    print("[MICRO-ENRICH] Sample rows:")
    for r in rows:
        print(
            f"  symbol={r.get('symbol')}, "
            f"ms_range_pct={r.get('ms_range_pct')}, "
            f"ms_trend_flag={r.get('ms_trend_flag')}, "
            f"est_spread_bps={r.get('est_spread_bps')}, "
            f"est_fee_bps={r.get('est_fee_bps')}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())