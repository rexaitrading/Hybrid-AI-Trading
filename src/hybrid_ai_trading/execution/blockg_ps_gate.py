from __future__ import annotations

import os
import subprocess
from pathlib import Path

from hybrid_ai_trading.runtime.context_loader import load_run_context_from_env


def enforce_blockg_via_powershell(symbol: str, where: str) -> None:
    """
    Canonical Block-G enforcement via PowerShell single source of truth.

    Fail-closed in LIVE:
      - runs tools/Check-BlockGReady.ps1 -Symbol <symbol>
      - requires exit code 0

    Override (NOT recommended):
      HAT_ALLOW_BLOCKG_BYPASS=1
    """
    sym = (symbol or "").strip().upper()
    if not sym:
        raise ValueError("symbol required")

    ctx = load_run_context_from_env()
    if not getattr(ctx, "is_live", False):
        return

    if (os.getenv("HAT_ALLOW_BLOCKG_BYPASS", "") or "").strip() == "1":
        return

    repo_root = Path(__file__).resolve().parents[2]
    ps1 = repo_root / "tools" / "Check-BlockGReady.ps1"
    if not ps1.exists():
        raise RuntimeError(f"[BLOCKG-MISSING] {ps1} not found; blocked at {where}")

    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", str(ps1),
        "-Symbol", sym,
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        out = (p.stdout or "").strip()
        err = (p.stderr or "").strip()
        msg = f"[BLOCKG-FAIL] {sym} blocked at {where}. Exit={p.returncode}."
        if out:
            msg += f" stdout={out}"
        if err:
            msg += f" stderr={err}"
        raise RuntimeError(msg)
