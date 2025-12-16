import json
import os
from pathlib import Path

import pytest

from hybrid_ai_trading.execution.blockg_guard import require_blockg_ready


def test_dev_replay_never_arms_live(tmp_path, monkeypatch):
    # Write a contract that looks superficially "green" except nvda_blockg_ready must remain False
    contract = {
        "as_of_date": "2025-12-15",
        "phase4_ok_today": True,
        "phase23_health_ok_today": True,
        "ev_hard_daily_ok_today": True,

        # GateScore may be true, but DEV_REPLAY must still not arm live.
        "gatescore_fresh_today": False,
        "gatescore_samples_ok_today": True,
        "gatescore_threshold_ok_today": True,
        "gatescore_ok_today": False,

        "nvda_blockg_ready": False,
        "spy_blockg_ready": False,
        "qqq_blockg_ready": False,
    }

    p = tmp_path / "blockg_status_stub.json"
    p.write_text(json.dumps(contract), encoding="utf-8")

    monkeypatch.setenv("HAT_BLOCKG_CONTRACT_PATH", str(p))

    with pytest.raises(Exception):
        require_blockg_ready("NVDA")