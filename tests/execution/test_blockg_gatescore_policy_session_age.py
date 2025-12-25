from __future__ import annotations

import json
from pathlib import Path

import pytest

from hybrid_ai_trading.execution.blockg_contract import ensure_symbol_blockg_ready


def test_gatescore_session_age_policy_allows_fresh_for_session(tmp_path: Path, monkeypatch):
    # Live intent
    monkeypatch.setenv("HAT_IS_PAPER", "0")

    status = {
        "phase4_ok_today": True,
        "ev_hard_daily_ok_today": True,
        "phase23_health_ok_today": True,
        # POLICY: fresh_today may be false on holidays/weekends
        "gatescore_fresh_today": False,
        "gatescore_fresh_for_session": True,
        "gatescore_recent_enough": True,
        "gatescore_age_days": 2,
        "gatescore_samples_ok": True,
        "gatescore_threshold_ok_today": True,
        "min_samples_ok_today": True,
        "nvda_blockg_ready": True,
    }

    p = tmp_path / "blockg_status_stub.json"
    p.write_text(json.dumps(status), encoding="utf-8")
    monkeypatch.setenv("HAT_BLOCKG_STATUS_PATH", str(p))

    # Must NOT raise (policy locked)
    ensure_symbol_blockg_ready("NVDA", allow_paper=False, is_paper=False)
