from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    """
    Emits logs/nvda_gatescore_samples.csv with columns: as_of_date, score

    This is a REAL producer only when it successfully computes a score from
    the NVDA GateScore engine. Otherwise, it writes header-only (fail-closed).
    """
    repo_root = Path(__file__).resolve().parents[1]
    logs = repo_root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    out = logs / "nvda_gatescore_samples.csv"
    today = datetime.now().strftime("%Y-%m-%d")

    # Default fail-closed: header-only
    def write_header_only() -> None:
        with out.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["as_of_date", "score"])

    try:
        from hybrid_ai_trading.replay.nvda_bplus_gate_score import compute_nvda_gatescore_today  # type: ignore
    except Exception:
        # API not present yet -> fail-closed header-only
        write_header_only()
        return 0

    try:
        score = float(compute_nvda_gatescore_today(repo_root))
    except Exception:
        write_header_only()
        return 0

    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["as_of_date", "score"])
        w.writerow([today, f"{score:.6f}"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
