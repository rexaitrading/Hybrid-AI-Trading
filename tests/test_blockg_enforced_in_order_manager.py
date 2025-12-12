from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from hybrid_ai_trading.execution.order_manager import OrderManager


class DummyLiveClient:
    def __init__(self):
        self.called = False

    def submit_order(self, symbol, side, qty, notional):
        self.called = True
        return {"status": "ok", "id": "DUMMY1"}


def _write_contract(repo_root: Path, ready: bool) -> None:
    logs = repo_root / "logs"
    logs.mkdir(exist_ok=True)
    p = logs / "blockg_status_stub.json"

    today = date.today().isoformat()
    payload = {
        "ts_utc": "2099-01-01T00:00:00.000Z",
        "as_of_date": today,
        "phase4_ok_today": True,
        "phase23_health_ok_today": True,
        "ev_hard_daily_ok_today": True,
        "gatescore_ok_today": True,
        "nvda_blockg_ready": bool(ready),
        "spy_blockg_ready": False,
        "qqq_blockg_ready": False,
    }
    p.write_text(json.dumps(payload), encoding="utf-8")


def test_order_manager_blocks_live_nvda_when_blockg_not_ready():
    repo_root = Path(__file__).resolve().parents[1]
    _write_contract(repo_root, ready=False)

    live = DummyLiveClient()
    om = OrderManager(dry_run=False, live_client=live)

    out = om.place_order("NVDA", "BUY", 1.0, 100.0)
    assert out["status"] == "blocked"
    assert "BLOCKG_NOT_READY" in out.get("reason", "")
    assert live.called is False


def test_order_manager_allows_live_nvda_when_blockg_ready():
    repo_root = Path(__file__).resolve().parents[1]
    _write_contract(repo_root, ready=True)

    live = DummyLiveClient()
    om = OrderManager(dry_run=False, live_client=live)

    out = om.place_order("NVDA", "BUY", 1.0, 100.0)
    assert live.called is True
    assert out.get("status") in ("pending", "filled", "ok")