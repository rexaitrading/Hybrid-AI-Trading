from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from hybrid_ai_trading.execution.blockg_enforce import BlockGNotReady
from hybrid_ai_trading.execution.execution_engine_phase5_guard import place_order_phase5_with_guard


class _DummyEngine:
    def __init__(self, is_paper: bool):
        self.is_paper = is_paper
        self.risk_manager = None
        self.config = {}


def _base_status(as_of_date: str) -> dict:
    # Minimal full contract fields required by blockg_contract.py daily gates
    return {
        "as_of_date": as_of_date,
        "phase4_ok_today": True,
        "ev_hard_daily_ok_today": True,
        "phase23_health_ok_today": True,
        "gatescore_fresh_today": True,
        "gatescore_samples_ok": True,
        "gatescore_threshold_ok_today": True,
        "reasons_not_ready": [],
    }


def test_live_path_blocks_when_blockg_not_ready(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HAT_IS_PAPER", "0")
    monkeypatch.setenv("HAT_BLOCKG_STATUS_PATH", str(tmp_path / "blockg_status_stub.json"))

    status = _base_status("2099-01-01")
    status["nvda_blockg_ready"] = False
    status["reasons_not_ready"] = ["stale", "nvda_blockg_ready=false"]

    (tmp_path / "blockg_status_stub.json").write_text(json.dumps(status), encoding="utf-8")

    eng = _DummyEngine(is_paper=False)

    with pytest.raises(BlockGNotReady):
        place_order_phase5_with_guard(
            engine=eng,
            symbol="NVDA",
            side="BUY",
            qty=1.0,
            price=100.0,
            regime="test",
        )


def test_live_path_allows_when_blockg_ready_today(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HAT_IS_PAPER", "0")
    monkeypatch.setenv("HAT_BLOCKG_STATUS_PATH", str(tmp_path / "blockg_status_stub.json"))

    status = _base_status(date.today().isoformat())
    status["nvda_blockg_ready"] = True

    (tmp_path / "blockg_status_stub.json").write_text(json.dumps(status), encoding="utf-8")

    eng = _DummyEngine(is_paper=False)

    out = place_order_phase5_with_guard(
        engine=eng,
        symbol="NVDA",
        side="BUY",
        qty=1.0,
        price=100.0,
        regime="test",
    )
    assert isinstance(out, dict)
    assert out.get("status")
