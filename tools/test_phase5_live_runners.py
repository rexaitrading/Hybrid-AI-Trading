from __future__ import annotations

"""
Tiny Phase-5 live-runner micro-suite.

Goals:
- Import NVDA / SPY / QQQ Phase-5 live-style runners.
- Run their main() once each with dry_run-style configs.
- Ensure EV bands + gating helpers are wired without crashes.

Intended to be called from tools/Test-Phase5Readiness.ps1.
"""

import sys
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

# Ensure BOTH repo root (for "tools.*") and src (for "config.*", "hybrid_ai_trading.*") are visible.
for p in (ROOT, SRC):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)


def run_runner(label: str, module_name: str, main_name: str = "main") -> None:
    print(f"[PHASE5_TEST] Importing {module_name} for {label} ...")
    mod = __import__(module_name, fromlist=["*"])
    print(f"[PHASE5_TEST] Imported {module_name} as {mod.__name__}")

    main: Callable[[], None] | None = getattr(mod, main_name, None)  # type: ignore[assignment]
    if main is None:
        print(f"[PHASE5_TEST][WARN] {module_name} has no {main_name}(), skipping dry run.")
        return

    print(f"[PHASE5_TEST] Running {module_name}.{main_name}() (dry_run assumed)...")
    main()
    print(f"[PHASE5_TEST] {module_name}.{main_name}() completed successfully for {label}.")


def main() -> None:
    try:
        run_runner("NVDA", "tools.nvda_phase5_live_smoke")
        run_runner("SPY", "tools.spy_orb_phase5_live_runner")
        run_runner("QQQ", "tools.qqq_orb_phase5_live_runner")
    except Exception as exc:
        print("[PHASE5_TEST][ERROR] Exception during Phase-5 live-runner test:", exc)
        # Let the exception propagate so the process exits non-zero.
        raise


if __name__ == "__main__":
    main()