from __future__ import annotations

"""
NVDA Phase-5 paper runner entrypoint (NO-IBG).

This file exists because tools/Invoke-NvdaPhase5PaperPipeline.ps1 expects it.
We keep it paper-safe: it delegates to the restored producer under tools/.
"""

# FAIL-CLOSED LIVE GUARD
# This module is intentionally PAPER-only (tools expect it).
# If anyone tries to run it as LIVE, we abort deterministically.
import os
import sys


def _fail_closed_if_live() -> None:
    mode = (os.getenv("HAT_RUN_MODE", "") or "").strip().upper()
    arm = (os.getenv("HAT_LIVE_ARM", "") or "").strip()
    argv = " ".join(sys.argv).upper()
    if mode == "LIVE" or arm == "1" or "--LIVE" in argv:
        raise SystemExit(
            "[BLOCKED] nvda_phase5_live_runner.py is PAPER-only. Refusing LIVE mode."
        )


_fail_closed_if_live()

import runpy
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main() -> int:
    target = _repo_root() / "tools" / "paper_live_without_ibg_nvda_phase5.py"
    if not target.exists():
        print(f"[NVDA-P5] FAIL-CLOSED: missing {target}")
        return 0

    # Execute as __main__ so argparse / main guards work as intended.
    runpy.run_path(str(target), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())