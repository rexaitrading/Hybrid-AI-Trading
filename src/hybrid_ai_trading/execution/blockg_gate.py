from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BlockGResult:
    symbol: str
    exit_code: int
    output: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


def _repo_root() -> Path:
    # Prefer walking up until .git found; fallback to CWD
    p = Path(__file__).resolve()
    for _ in range(10):
        if (p / ".git").exists():
            return p
        p = p.parent
    return Path(os.getcwd()).resolve()


def check_blockg_ready(symbol: str) -> BlockGResult:
    sym = (symbol or "").upper().strip()
    if sym not in ("NVDA", "SPY", "QQQ"):
        raise ValueError(f"Unsupported symbol: {symbol!r}")

    root = _repo_root()
    script = root / "tools" / "Check-BlockGReady.ps1"
    if not script.exists():
        raise FileNotFoundError(f"Missing Block-G checker: {script}")

    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-Symbol",
        sym,
    ]

    proc = subprocess.run(
        cmd,
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return BlockGResult(symbol=sym, exit_code=int(proc.returncode), output=out)

def run_blockg_check(symbol: str) -> BlockGResult:
    """
    Compatibility wrapper: OrderManager imports run_blockg_check.
    Block-G semantics remain PS-authoritative via tools\Check-BlockGReady.ps1.
    """
    return check_blockg_ready(symbol)
