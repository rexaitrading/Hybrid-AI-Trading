from __future__ import annotations

import json
from pathlib import Path

import pytest

from hybrid_ai_trading.execution.order_manager import OrderManager
from hybrid_ai_trading.execution.blockg_enforce import BlockGNotReady


class _IbLikeLive:
    """
    IB-like stub: presence of placeOrder makes OrderManager treat it as IB.
    submit_order must NOT be called when Block-G not ready.
    """
    def __init__(self):
        self.called_submit = False

    def placeOrder(self, *a, **k):
        # Not used in this test; only here to trip is_ib_like.
        return None

    def submit_order(self, *a, **k):
        self.called_submit = True
        return {"status": "pending", "order_id": "X"}


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
        "nvda_blockg_ready": bool(nvda_ready),
        "spy_blockg_ready": False,
        "qqq_blockg_ready": False,
        "reasons_not_ready": [],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_order_manager_blocks_live_nvda_before_submit(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HAT_IS_PAPER", "0")

    status_path = tmp_path / "blockg_status_stub.json"
    _write_blockg(status_path, nvda_ready=False)
    monkeypatch.setenv("HAT_BLOCKG_STATUS_PATH", str(status_path))

    live = _IbLikeLive()
    om = OrderManager(live_client=live, dry_run=False)

    with pytest.raises(BlockGNotReady):
        om.place_order(symbol="NVDA", side="BUY", size=1.0, ctx=None, price=1.0)

    assert live.called_submit is False


def test_order_manager_allows_live_nvda_when_ready(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HAT_IS_PAPER", "0")

    status_path = tmp_path / "blockg_status_stub.json"
    _write_blockg(status_path, nvda_ready=True)
    monkeypatch.setenv("HAT_BLOCKG_STATUS_PATH", str(status_path))

    live = _IbLikeLive()
    om = OrderManager(live_client=live, dry_run=False)

    om.place_order(symbol="NVDA", side="BUY", size=1.0, ctx=None, price=1.0)
    assert live.called_submit is True
