from __future__ import annotations

import csv
import subprocess
import sys
from datetime import date
from pathlib import Path


def test_phase23_quick_appends_today_row():
    repo_root = Path(__file__).resolve().parents[1]
    ps1 = repo_root / "tools" / "Run-Phase23Quick.ps1"
    assert ps1.exists(), "Run-Phase23Quick.ps1 missing"

    logs = repo_root / "logs"
    logs.mkdir(exist_ok=True)
    out_csv = logs / "phase23_health_daily.csv"

    # Run Phase23 quick
    p = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, f"Phase23Quick failed:\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}"

    assert out_csv.exists(), "phase23_health_daily.csv not written"

    today = date.today().isoformat()
    with out_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    assert rows, "phase23_health_daily.csv empty"
    assert rows[-1].get("date", "")[:10] == today, f"Last row date != today ({today})"