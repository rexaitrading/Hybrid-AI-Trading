from __future__ import annotations

import json
from pathlib import Path

import pytest

from hybrid_ai_trading.execution.blockg_enforce import BlockGNotReady


def _write_status(tmp_path: Path, *, nvda_ready: bool) -> str:
    p = tmp_path / "blockg_status_stub.json"
    p.write_text(
        json.dumps(
            {
                "phase4_ok_today": True,
                "ev_hard_daily_ok_today": True,
                "gatescore_fresh_today": True,
                "gatescore_fresh_for_session": True,
                "gatescore_recent_enough": True,
                "gatescore_age_days": 0,
                "gatescore_samples_ok": True,
                "gatescore_threshold_ok_today": True,
                "gatescore_ok_today": True,
                "min_samples_ok_today": True,
                "nvda_blockg_ready": nvda_ready,
                "spy_blockg_ready": False,
                "qqq_blockg_ready": False,
                "reasons_not_ready": ([] if nvda_ready else ["nvda_blockg_ready=false"]),
            }
        ),
        encoding="utf-8",
    )
    return str(p)


def test_order_manager_blocks_live_without_blockg(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HAT_IS_PAPER", "0")
    monkeypatch.setenv("HAT_BLOCKG_STATUS_PATH", _write_status(tmp_path, nvda_ready=False))

    import hybrid_ai_trading.order_manager as om

    with pytest.raises(BlockGNotReady):
        om._blockg_guard_if_live("NVDA")
