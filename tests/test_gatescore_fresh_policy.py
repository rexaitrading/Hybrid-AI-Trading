from __future__ import annotations

import json
import subprocess
from pathlib import Path

def _run_ps(script: str) -> str:
    p = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script],
        capture_output=True,
        text=True,
        check=True,
    )
    return p.stdout

def test_gatescore_fresh_today_vs_session_policy(tmp_path: Path, monkeypatch):
    # Run builder to refresh logs/blockg_status_stub.json
    out = _run_ps(r".\tools\Build-BlockGStatusStub.ps1")
    assert "blockg_status_stub.json" in out.lower()

    st_path = Path("logs") / "blockg_status_stub.json"
    assert st_path.exists()

    st = json.loads(st_path.read_text(encoding="utf-8"))

    # Policy invariants:
    # fresh_for_session can be True on weekends/holidays (session date != today_utc)
    # fresh_today must only be True if session date == as_of_date (UTC today)
    today = st.get("as_of_date")
    gs_asof = st.get("gatescore_as_of_date")

    assert isinstance(today, str) and len(today) >= 10
    assert isinstance(gs_asof, str) and len(gs_asof) >= 10

    fresh_session = bool(st.get("gatescore_fresh_for_session"))
    fresh_today = bool(st.get("gatescore_fresh_today"))

    if gs_asof != today:
        assert fresh_today is False, "fresh_today must be False when session != today"
    else:
        # If same day, fresh_today must mirror fresh_for_session
        assert fresh_today == fresh_session
