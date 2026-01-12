from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hybrid_ai_trading.broker.ib_safe import ib_place_order_chokepoint
from hybrid_ai_trading.execution.blockg_enforce import BlockGNotReady


class _C:
    def __init__(self, symbol: str):
        self.symbol = symbol


class _IB:
    def __init__(self):
        self.called = False

    # Support both call styles; chokepoint tries (order_id, contract, order) then (contract, order)
    def placeOrder(self, *a, **k):
        self.called = True
        return None



def _write_nvda_stamp_ready(tmp_path: Path) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    p = tmp_path / "nvda_live_ready_stamp.json"
    p.write_text(
        json.dumps({"ts_utc": "2025-01-01T00:00:00Z", "as_of_date": today, "nvda_live_ready": True}),
        encoding="utf-8",
    )
    return p

def _write_blockg(path: Path, *, nvda_ready: bool) -> None:
    payload = {
        "ts_utc": "2025-01-01T00:00:00Z",
        "as_of_date": "2025-01-01",
        "phase23_health_ok_today": True,
        "ev_hard_daily_ok_today": True,
        "ev_hard_as_of_date": "2025-01-01",
        "ev_hard_session_ok": True,
        "phase4_ok_today": True,
        "gatescore_as_of_date": "2025-01-01",
        "gatescore_age_days": 0,
        "gatescore_recent_enough": True,
        "gatescore_fresh_today": True,
        "gatescore_fresh_for_session": True,
        "gatescore_samples_ok": True,
        "min_samples_ok_today": True,
        "gatescore_threshold_ok_today": True,
        "gatescore_ok_today": True,
        "contract_semantics_level": "FULL_LIVE_ELIGIBLE",
        "nvda_blockg_ready": bool(nvda_ready),
        "spy_blockg_ready": False,
        "qqq_blockg_ready": False,
        "reasons_not_ready": [],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_ib_placeorder_blocks_live_nvda_when_not_ready(tmp_path: Path, monkeypatch):
    # Force LIVE
    monkeypatch.setenv("HAT_IS_PAPER", "0")
    stamp = _write_nvda_stamp_ready(tmp_path)
    monkeypatch.setenv("HAT_LIVE_READY_STAMP_PATH", str(stamp))
    token = tmp_path / "live_arm_nvda.json"
    token.write_text(json.dumps({"symbol":"NVDA","as_of_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "armed": True}) + "\n", encoding="utf-8")
    monkeypatch.setenv("HAT_LIVE_ARM_TOKEN_PATH", str(token))

    # Point contract reader to our temp JSON
    status_path = tmp_path / "blockg_status_stub.json"
    _write_blockg(status_path, nvda_ready=False)
    monkeypatch.setenv("HAT_BLOCKG_STATUS_PATH", str(status_path))

    ib = _IB()
    contract = _C("NVDA")
    order = object()

    with pytest.raises(BlockGNotReady):
        ib_place_order_chokepoint(ib, contract, order)

    assert ib.called is False


def test_ib_placeorder_allows_live_nvda_when_ready(tmp_path: Path, monkeypatch):
    # Deterministic allow-test: PS ALL_STRICT includes market_session_open_now (time-dependent).
    # Patch the exact imported symbol used by ib_safe chokepoint.
    import hybrid_ai_trading.broker.ib_safe as ibsafe
    monkeypatch.setattr(ibsafe, "require_blockg_ready_via_powershell", lambda *a, **k: None)

    monkeypatch.setenv("HAT_IS_PAPER", "0")
    stamp = _write_nvda_stamp_ready(tmp_path)
    monkeypatch.setenv("HAT_LIVE_READY_STAMP_PATH", str(stamp))
    token = tmp_path / "live_arm_nvda.json"
    token.write_text(json.dumps({"symbol":"NVDA","as_of_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "armed": True}) + "\n", encoding="utf-8")
    monkeypatch.setenv("HAT_LIVE_ARM_TOKEN_PATH", str(token))
    status_path = tmp_path / "blockg_status_stub.json"
    _write_blockg(status_path, nvda_ready=True)
    monkeypatch.setenv("HAT_BLOCKG_STATUS_PATH", str(status_path))

    ib = _IB()
    contract = _C("NVDA")
    order = object()

    ib_place_order_chokepoint(ib, contract, order)
    assert ib.called is True
