from __future__ import annotations

import os
import csv
from datetime import datetime
from pathlib import Path


def main() -> int:
    # ------------------------------------------------------------
    # HARD SAFETY GATES
    # ------------------------------------------------------------

    # 1) LIVE MODE: absolutely forbidden
    run_mode = (os.environ.get("HAT_RUN_MODE") or "").lower()
    if run_mode == "live":
        raise SystemExit("Replay GateScore sampling disabled in LIVE mode")

    # 2) ARM INTENT: explicit human intent required
    arm = (os.environ.get("HAT_ARM_REPLAY_GATESCORE") or "").strip().lower()
    if arm not in ("1", "true", "yes", "y", "on"):
        raise SystemExit(
            "Replay GateScore sampling requires HAT_ARM_REPLAY_GATESCORE=1"
        )

    # ------------------------------------------------------------
    # PATHS
    # ------------------------------------------------------------
    repo_root = Path(__file__).resolve().parents[1]
    logs = repo_root / "logs"
    logs.mkdir(parents=True, exist_ok=True)

    out = logs / "nvda_gatescore_samples.csv"
    today = datetime.now().strftime("%Y-%m-%d")

    # ------------------------------------------------------------
    # FAIL-CLOSED DEFAULTS
    # ------------------------------------------------------------
    score = 0.0
    count_signals = 0
    pnl_samples = 0

    try:
        from hybrid_ai_trading.replay.nvda_bplus_gate_score import (
            compute_nvda_gatescore_today,
        )

        score = float(compute_nvda_gatescore_today(repo_root))
        count_signals = int(globals().get("_NVDA_GS_COUNT_SIGNALS", 1))
        pnl_samples = int(globals().get("_NVDA_GS_PNL_SAMPLES", 1))
    except Exception:
        # remain fail-closed
        pass

    # ------------------------------------------------------------
    # APPEND-SAFE WRITE
    # ------------------------------------------------------------
    need_header = not out.exists()
    mode = "a" if out.exists() else "w"

    with out.open(mode, encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if need_header:
            w.writerow(["as_of_date", "score", "count_signals", "pnl_samples"])
        w.writerow([today, f"{score:.6f}", count_signals, pnl_samples])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
