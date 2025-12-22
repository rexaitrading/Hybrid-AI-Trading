from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS = REPO_ROOT / "tools"
LOGS = REPO_ROOT / "logs"


def _run_ps(script: str, *args: str) -> int:
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(TOOLS / script),
        *args,
    ]
    p = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    if p.returncode != 0:
        print("STDOUT:\n", p.stdout)
        print("STDERR:\n", p.stderr)
    return p.returncode


@pytest.mark.parametrize("nvda_ready,expected", [(True, 0), (False, 2)])
def test_phase5_todayness_trusts_blockg_checker(nvda_ready: bool, expected: int):
    LOGS.mkdir(parents=True, exist_ok=True)
    status_path = LOGS / "blockg_status_stub.json"

    backup = status_path.read_text(encoding="utf-8") if status_path.exists() else None
    today = date.today().isoformat()

    payload = {
        "ts_utc": f"{today}T00:00:00Z",
        "as_of_date": today,

        "phase23_health_ok_today": True,
        "ev_hard_daily_ok_today": True,
        "ev_hard_as_of_date": today,
        "ev_hard_session_ok": True,

        "phase4_ok_today": True,

        "gatescore_as_of_date": today,
        "gatescore_fresh_today": True,
        "gatescore_fresh_for_session": True,
        "gatescore_samples_ok": True,
        "min_samples_ok_today": True,
        "gatescore_threshold_ok_today": True,
        "gatescore_ok_today": True,

        "nvda_blockg_ready": nvda_ready,
        "spy_blockg_ready": False,
        "qqq_blockg_ready": False,

        "reasons_not_ready": [],
    }

    status_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    try:
        rc_blockg = _run_ps("Check-BlockGReady.ps1", "-Symbol", "NVDA")
        rc_phase5 = _run_ps("Check-Phase5Today.ps1", "-Symbol", "NVDA")
        assert rc_blockg == expected
        assert rc_phase5 == expected
    finally:
        if backup is not None:
            status_path.write_text(backup, encoding="utf-8")
        else:
            try:
                status_path.unlink()
            except FileNotFoundError:
                pass
