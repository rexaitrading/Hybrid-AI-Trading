from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)


def test_phase5_risk_schema_validator_cli() -> None:
    """CLI-level check: schema validator must succeed on current configs."""

    cfgs = [
        "config/orb_vwap_aapl_thresholds.json",
        "config/orb_vwap_nvda_thresholds.json",
        "config/orb_vwap_spy_thresholds.json",
        "config/orb_vwap_qqq_thresholds.json",
    ]

    cmd = [sys.executable, "tools/phase5_risk_schema_validator.py", *cfgs]
    proc = run(cmd)

    print(proc.stdout)
    print(proc.stderr, file=sys.stderr)

    assert proc.returncode == 0, "Phase5 risk schema validator failed"


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="Diff tool uses PowerShell (Windows-only)")
def test_phase5_risk_diff_tool_cli() -> None:
    """CLI-level check: Phase5 diff tool runs successfully on AAPL vs NVDA."""

    # Use Windows PowerShell entrypoint; CI for this project is Windows-focused.
    ps_exe = os.environ.get("COMSPEC", "cmd.exe")
    # We prefer powershell if available, but as a minimal approach we call via cmd /c powershell ...
    # This keeps us robust on Windows agents.
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "tools/Diff-Phase5Configs.ps1",
        "-Left",
        "config/orb_vwap_aapl_thresholds.json",
        "-Right",
        "config/orb_vwap_nvda_thresholds.json",
    ]

    proc = run(cmd)

    print(proc.stdout)
    print(proc.stderr, file=sys.stderr)

    assert proc.returncode == 0, "Phase5 risk diff tool failed to run"