from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


def main() -> int:
    """
    Emit logs/nvda_gatescore_samples.csv with columns: as_of_date, score

    Fail-closed:
      - if compute fails, write header-only.
    """
    repo_root = Path(__file__).resolve().parents[1]
    logs = repo_root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    out = logs / "nvda_gatescore_samples.csv"
    today = datetime.now().strftime("%Y-%m-%d")

    def write_header_only() -> None:
        with out.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["as_of_date","score","count_signals","pnl_samples"])

    print("DEBUG: emit_nvda_gatescore_samples starting")
    print(f"DEBUG: repo_root={repo_root}")

    try:
        from hybrid_ai_trading.replay.nvda_bplus_gate_score import compute_nvda_gatescore_today
    except Exception as e:
        print(f"DEBUG: import failed: {e!r}")
        write_header_only()
        return 0

    try:
        score = float(compute_nvda_gatescore_today(repo_root))
count_signals = int(globals().get("_NVDA_GS_COUNT_SIGNALS", 1))
pnl_samples   = int(globals().get("_NVDA_GS_PNL_SAMPLES", 1))
    except Exception as e:
        print(f"DEBUG: compute failed: {e!r}")
        write_header_only()
        return 0

    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["as_of_date","score","count_signals","pnl_samples"])
        w.writerow([today, f"{score:.6f}", count_signals, pnl_samples])

    print(f"DEBUG: wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

