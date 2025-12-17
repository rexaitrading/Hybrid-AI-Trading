from __future__ import annotations

import json
from pathlib import Path

import pytest

from hybrid_ai_trading.execution.execution_engine_phase5_guard import place_order_phase5_with_guard


class DummyEngine:
    def __init__(self, is_paper: bool) -> None:
        self.is_paper = is_paper
        self.risk_manager = None


def write_contract(tmp_path: Path, ready: bool) -> Path:
    p = tmp_path / "blockg_status_stub_nvda.json"
    payload = {
        "as_of_date": "2099-01-01",
        "phase4_ok_today": True,
        "phase23_health_ok_today": True,
        "ev_hard_daily_ok_today": True,
        "gatescore_fresh_today": True,
        "nvda_blockg_ready": ready,
    }
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return p


def test_live_fails_closed_when_contract_missing(monkeypatch):
    monkeypatch.setenv('IBKR_LIVE','1')
    monkeypatch.setenv("HAT_BLOCKG_CONTRACT_PATH", r"Z:\__missing__\blockg.json")

    with pytest.raises(Exception):
        place_order_phase5_with_guard(
            DummyEngine(is_paper=False),
            symbol="NVDA",
            side="BUY",
            qty=1,
            price=100.0,
            regime="NVDA_BPLUS_LIVE",
            day_id="TEST",
        )


def test_live_allows_when_contract_ready(monkeypatch, tmp_path):
    p = write_contract(tmp_path, ready=True)
    monkeypatch.setenv("HAT_BLOCKG_CONTRACT_PATH", str(p))

    out = place_order_phase5_with_guard(
        DummyEngine(is_paper=False),
        symbol="NVDA",
        side="BUY",
        qty=1,
        price=100.0,
        regime="NVDA_BPLUS_LIVE",
        day_id="TEST",
    )
    assert str(out.get("status", "")).startswith("ok")