from __future__ import annotations

import json
import subprocess
from pathlib import Path

def test_phase7_daily_artifact_writes_json() -> None:
    repo = Path(__file__).resolve().parents[1]
    ps1 = repo / "tools" / "Build-PortfolioOptimizerDaily.ps1"
    assert ps1.exists()

    p = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, p.stdout + "\n" + p.stderr

    logs = repo / "logs"
    files = sorted(logs.glob("portfolio_optimizer_daily_*.json"))
    assert files, "expected portfolio_optimizer_daily_*.json to be created"

    data = json.loads(files[-1].read_text(encoding="utf-8"))
    for k in ("ts_utc", "as_of_date", "status", "constraints_ok", "allocations"):
        assert k in data