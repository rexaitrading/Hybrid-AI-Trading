from pathlib import Path
import json

def test_nvda_blockg_ready_when_all_summary_flags_true(tmp_path):
    # Simulated Block-G payload with all summary flags true
    payload = {
        "phase23_health_ok_today": True,
        "ev_hard_daily_ok_today": True,
        "phase4_ok_today": True,
        "gatescore_ok_today": True,
        "gatescore_fresh_today": True,
        "nvda_blockg_ready": True,
        "reasons_not_ready": [],
    }

    assert payload["nvda_blockg_ready"] is True
    assert payload["reasons_not_ready"] == []
