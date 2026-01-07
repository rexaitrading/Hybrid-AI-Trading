"""
Phase-7 PortfolioGate — PowerShell single authority.

Python MUST NOT re-implement portfolio semantics.
It shells out to tools\\Check-PortfolioGate.ps1 and fail-closes on non-zero.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioGateResult:
    ok: bool
    rc: int
    cmd: str


class PortfolioGateError(RuntimeError):
    pass


def _repo_root_from_here() -> str:
    # .../src/hybrid_ai_trading/execution/portfolio_ps_checker.py -> repo root
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.abspath(os.path.join(here, os.pardir, os.pardir, os.pardir))


def require_portfolio_gate_via_powershell(symbol: str, *, timeout_sec: int = 30) -> PortfolioGateResult:
    sym = (symbol or "").upper().strip()
    if not sym:
        raise PortfolioGateError("PortfolioGate: empty symbol")

    repo_root = _repo_root_from_here()
    ps1 = os.path.join(repo_root, "tools", "Check-PortfolioGate.ps1")
    if not os.path.exists(ps1):
        raise PortfolioGateError(f"PortfolioGate: missing PS checker: {ps1}")

    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        ps1,
        "-Symbol",
        sym,
    ]

    try:
        p = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as e:
        raise PortfolioGateError(f"PortfolioGate: timeout after {timeout_sec}s") from e

    out = (p.stdout or "").strip()
    err = (p.stderr or "").strip()

    if p.returncode != 0:
        msg = f"PortfolioGate FAIL-CLOSED rc={p.returncode} sym={sym}"
        if out:
            msg += f"\\nSTDOUT:\\n{out}"
        if err:
            msg += f"\\nSTDERR:\\n{err}"
        raise PortfolioGateError(msg)

    return PortfolioGateResult(ok=True, rc=p.returncode, cmd=" ".join(cmd))