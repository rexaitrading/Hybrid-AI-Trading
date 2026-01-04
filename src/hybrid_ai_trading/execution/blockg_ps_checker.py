from __future__ import annotations

import os
import subprocess
from pathlib import Path

from hybrid_ai_trading.execution.blockg_errors import BlockGNotReady


def _repo_root() -> Path:
    # .../src/hybrid_ai_trading/execution -> repo root is 4 parents up
    return Path(__file__).resolve().parents[3]


def _ps_exe() -> str:
    # Prefer Windows PowerShell 5.1; allow override if needed
    return (os.environ.get("HAT_POWERSHELL_EXE") or "").strip() or "powershell"


def require_blockg_ready_via_powershell(symbol: str, *, build: bool = False) -> None:
    """
    Institutional: tools\\Check-BlockGReady.ps1 is the single semantic owner.
    Fail-closed on any non-zero exit code.
    """
    sym = (symbol or "").upper().strip()
    if sym not in {"NVDA", "SPY", "QQQ"}:
        raise BlockGNotReady(f"BLOCK-G FAIL-CLOSED: unsupported_symbol={sym}")

    script = _repo_root() / "tools" / "Check-BlockGReady.ps1"
    if not script.exists():
        raise BlockGNotReady(f"BLOCK-G FAIL-CLOSED: missing_checker={script.as_posix()}")

    args = [
        _ps_exe(),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-Symbol",
        sym,
    ]
    if build:
        args.append("-Build")

    cp = subprocess.run(args, capture_output=True, text=True, cwd=str(_repo_root()), timeout=30)

    if cp.returncode != 0:
        out = (cp.stdout or "")[-1500:].strip()
        err = (cp.stderr or "")[-1500:].strip()
        msg = f"BLOCK-G FAIL-CLOSED: ps_checker_exit={cp.returncode} symbol={sym}"
        if cp.returncode == 10:
            msg += "\n[BLOCKG] NOTE: exit=10 is closed-day DIAGNOSTIC OK; LIVE remains disallowed (fail-closed)."
        if out:
            msg += "\n" + out
        if err:
            msg += "\n" + err
        raise BlockGNotReady(msg)


def check_blockg_diagnostic_ok(symbol: str, *, build: bool = False) -> None:
    """
    Ops-only: accept ps_checker_exit=10 (closed-day diagnostic OK).
    NEVER use this for live order gating.
    """
    try:
        require_blockg_ready_via_powershell(symbol, build=build)
    except BlockGNotReady as e:
        if "ps_checker_exit=10" in str(e):
            return
        raise
