from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path

from hybrid_ai_trading.execution.blockg_errors import BlockGNotReady


def _repo_root() -> Path:
    # .../src/hybrid_ai_trading/execution -> repo root is 4 parents up
    return Path(__file__).resolve().parents[3]


def _ps_exe() -> str:
    # Prefer Windows PowerShell 5.1; allow override if needed
    return (os.environ.get("HAT_POWERSHELL_EXE") or "").strip() or "powershell"


def _audit_log(sym: str, *, stdout: str, stderr: str, returncode: int | None, note: str = "") -> str:
    """
    Best-effort audit log. Returns log path (string) or empty string on failure.
    """
    try:
        log_dir = _repo_root() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        log_path = log_dir / f"blockg_ps_check_{sym}_{ts}.log"
        rc = "" if returncode is None else str(returncode)
        body = (
            f"ts_utc={datetime.utcnow().isoformat()}Z\n"
            f"symbol={sym}\n"
            f"returncode={rc}\n"
        )
        if note:
            body += f"note={note}\n"
        body += "\n=== STDOUT ===\n" + (stdout or "") + "\n"
        body += "\n=== STDERR ===\n" + (stderr or "") + "\n"
        log_path.write_text(body, encoding="utf-8")
        return log_path.as_posix()
    except Exception:
        return ""


def require_blockg_ready_via_powershell(
    symbol: str,
    *,
    market: str | None = None,
    build: bool = False,
    timeout_s: int = 30,
) -> None:
    """
    Institutional: tools\\Check-BlockGReady.ps1 is the single semantic owner.
    Fail-closed on any non-zero exit code.
    Always writes an audit log to logs/ (best-effort).
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
    ]
    # Market routing (A3): default US if not provided.
    mk = (market or "").upper().strip()
    if mk:
        args += ["-Market", mk]
    args += [
        "-Symbol",
        sym,
    ]
    if build:
        args.append("-Build")

    try:
        cp = subprocess.run(
            args,
            capture_output=True,
            text=True,
            cwd=str(_repo_root()),
            timeout=int(timeout_s),
        )
    except subprocess.TimeoutExpired as e:
        out = e.stdout or ""
        err = e.stderr or ""
        logp = _audit_log(sym, stdout=out, stderr=err, returncode=None, note=f"timeout_s={timeout_s}")
        msg = f"BLOCK-G FAIL-CLOSED: ps_timeout symbol={sym} timeout_s={timeout_s}"
        if logp:
            msg += f"\nlog={logp}"
        raise BlockGNotReady(msg)

    # Always audit (even success)
    note = ""
    if cp.returncode == 10:
        note = "exit=10 closed-day DIAGNOSTIC OK; LIVE remains disallowed"
    logp = _audit_log(sym, stdout=cp.stdout or "", stderr=cp.stderr or "", returncode=cp.returncode, note=note)

    if cp.returncode != 0:
        out = (cp.stdout or "")[-1500:].strip()
        err = (cp.stderr or "")[-1500:].strip()
        msg = f"BLOCK-G FAIL-CLOSED: ps_checker_exit={cp.returncode} symbol={sym}"
        if cp.returncode == 10:
            msg += "\n[BLOCKG] NOTE: exit=10 is closed-day DIAGNOSTIC OK; LIVE remains disallowed (fail-closed)."
        if logp:
            msg += f"\nlog={logp}"
        if out:
            msg += "\n" + out
        if err:
            msg += "\n" + err
        raise BlockGNotReady(msg)


def check_blockg_diagnostic_ok(symbol: str, *, market: str | None = None, build: bool = False) -> None:
    """
    Ops-only: accept ps_checker_exit=10 (closed-day diagnostic OK).
    NEVER use this for live order gating.
    """
    try:
        require_blockg_ready_via_powershell(symbol, market=market, build=build)
    except BlockGNotReady as e:
        if "ps_checker_exit=10" in str(e):
            return
        raise