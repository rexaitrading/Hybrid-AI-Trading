from __future__ import annotations

import csv
from pathlib import Path

from hybrid_ai_trading.microstructure.regime import classify_micro_regime


def _try_float(v: object, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        s = str(v).strip()
        if not s:
            return default
        return float(s)
    except Exception:
        return default


def main() -> int:
    """
    Phase-2 microstructure enrichment (v1).

    - Reads logs/spy_qqq_micro_for_notion.csv
    - Adds micro_regime=classify_micro_regime(ms_range_pct, est_spread_bps, est_fee_bps)
    - Writes logs/spy_qqq_micro_for_notion_enriched.csv (does NOT overwrite original)
    - Best-effort: never gates, always exit 0.
    """
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[1]
    logs_dir = repo_root / "logs"
    in_path = logs_dir / "spy_qqq_micro_for_notion.csv"
    out_path = logs_dir / "spy_qqq_micro_for_notion_enriched.csv"

    if not in_path.exists():
        print("[MICRO-ENRICH] SKIP: spy_qqq_micro_for_notion.csv not found (nothing to enrich).")
        return 0

    try:
        with in_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = list(reader.fieldnames or [])
    except Exception as e:
        print(f"[MICRO-ENRICH] ERROR reading spy_qqq_micro_for_notion.csv: {e!r}")
        return 0

    if not rows:
        print("[MICRO-ENRICH] No data rows found in spy_qqq_micro_for_notion.csv")
        return 0

    if "micro_regime" not in fieldnames:
        fieldnames.append("micro_regime")

    for r in rows:
        ms_range_pct = _try_float(r.get("ms_range_pct"), 0.0)
        est_spread_bps = _try_float(r.get("est_spread_bps"), 0.0)
        est_fee_bps = _try_float(r.get("est_fee_bps"), 0.0)
        r["micro_regime"] = classify_micro_regime(ms_range_pct, est_spread_bps, est_fee_bps)

    try:
        with out_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow(r)
    except Exception as e:
        print(f"[MICRO-ENRICH] ERROR writing enriched CSV: {e!r}")
        return 0

    print("[MICRO-ENRICH] Wrote enriched CSV -> logs/spy_qqq_micro_for_notion_enriched.csv")
    print("[MICRO-ENRICH] Sample rows:")
    for r in rows[:10]:
        print(
            f"  symbol={r.get('symbol')}, "
            f"ms_range_pct={r.get('ms_range_pct')}, "
            f"est_spread_bps={r.get('est_spread_bps')}, "
            f"est_fee_bps={r.get('est_fee_bps')}, "
            f"micro_regime={r.get('micro_regime')}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())