from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from hybrid_ai_trading.execution.execution_engine_phase5_guard import place_order_phase5_with_guard
from hybrid_ai_trading.runtime.run_context import RunContext, RunMode


class DummyEngine:
    def __init__(self, is_paper: bool, ctx: RunContext) -> None:
        self.is_paper = is_paper
        self.run_context = ctx
        self.risk_manager = None


def _write_contract(p: Path, *, as_of_date: str, nvda_ready: bool) -> None:
    payload = {
        "ts_utc": "TEST",
        "as_of_date": as_of_date,
        "nvda_blockg_ready": bool(nvda_ready),
        "spy_blockg_ready": False,
        "qqq_blockg_ready": False,
        # include the fields checker expects but guard only needs nvda_blockg_ready
        "phase4_ok_today": True,
        "phase23_health_ok_today": True,
        "ev_hard_daily_ok_today": True,
        "gatescore_ok_today": True,
    }
    p.write_text(json.dumps(payload), encoding="utf-8")


def test_live_nvda_blocked_when_contract_not_ready(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    today = "2025-12-18"  # fixed date matches your local logs; adjust if your suite uses dynamic today elsewhere
    contract = tmp_path / "blockg.json"
    _write_contract(contract, as_of_date=today, nvda_ready=False)

    monkeypatch.setenv("HAT_BLOCKG_CONTRACT_PATH", str(contract))

    ctx = RunContext(mode=RunMode.LIVE)
    eng = DummyEngine(is_paper=False, ctx=ctx)

    with pytest.raises(RuntimeError) as e:
        place_order_phase5_with_guard(
            eng,
            symbol="NVDA",
            side="BUY",
            qty=1,
            price=100.0,
            regime="NVDA_BPLUS_LIVE",
            day_id="TEST",
        )
    assert "BLOCK-G NOT READY" in str(e.value) or "BLOCKG_DENY" in str(e.value)


def test_live_nvda_allowed_when_contract_ready(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    today = "2025-12-18"
    contract = tmp_path / "blockg.json"
    _write_contract(contract, as_of_date=today, nvda_ready=True)

    monkeypatch.setenv("HAT_BLOCKG_CONTRACT_PATH", str(contract))

    ctx = RunContext(mode=RunMode.LIVE)
    eng = DummyEngine(is_paper=False, ctx=ctx)

    out = place_order_phase5_with_guard(
        eng,
        symbol="NVDA",
        side="BUY",
        qty=1,
        price=100.0,
        regime="NVDA_BPLUS_LIVE",
        day_id="TEST",
    )
    assert out["status"].startswith("ok")