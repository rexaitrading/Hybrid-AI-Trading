from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


def _write_utf8(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj), encoding="utf-8", newline="\n")


def _run_ps_checker(repo_root: Path, symbol: str) -> int:
    ps1 = repo_root / "tools" / "Check-BlockGReady.ps1"
    p = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1), "-Symbol", symbol],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    return p.returncode


def test_checker_exits_3_on_stale_contract(tmp_path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    contract = repo_root / "logs" / "blockg_status_stub.json"
    bak = contract.read_text(encoding="utf-8", errors="ignore") if contract.exists() else None

    try:
        _write_utf8(contract, {
            "as_of_date": "1999-01-01",
            "nvda_blockg_ready": True,
            "spy_blockg_ready": True,
            "qqq_blockg_ready": True,
        })
        rc = _run_ps_checker(repo_root, "NVDA")
        assert rc == 3
    finally:
        if bak is None:
            contract.unlink(missing_ok=True)
        else:
            contract.write_text(bak, encoding="utf-8", newline="\n")


def test_checker_exits_3_when_symbol_field_missing(tmp_path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    contract = repo_root / "logs" / "blockg_status_stub.json"
    bak = contract.read_text(encoding="utf-8", errors="ignore") if contract.exists() else None

    try:
        # no spy_blockg_ready field
        _write_utf8(contract, {
            "as_of_date": "2025-12-11",
            "nvda_blockg_ready": True,
        })
        rc = _run_ps_checker(repo_root, "SPY")
        assert rc == 3
    finally:
        if bak is None:
            contract.unlink(missing_ok=True)
        else:
            contract.write_text(bak, encoding="utf-8", newline="\n")