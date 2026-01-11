from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hybrid_ai_trading.execution.blockg_enforce import BlockGNotReady
from hybrid_ai_trading.broker.ib_safe import ib_place_order_chokepoint


class _C:
    def __init__(self, symbol: str):
        self.symbol = symbol


class _O:
    pass


class _IB:
    def __init__(self):
        self.called = False
        self.args = None

    def placeOrder(self, *a, **k):
        self.called = True
        self.args = (a, k)
        return object()


def _write_status(tmp_path: Path, *, nvda_ready: bool) -> Path:
    p = tmp_path / "blockg_status_stub.json"
    p.write_text(
        json.dumps(
            {
                "phase4_ok_today": True,
                "ev_hard_daily_ok_today": True,
                "gatescore_fresh_for_session": True,
                "gatescore_fresh_today": True,
                "gatescore_samples_ok": True,
                "gatescore_threshold_ok_today": True,
                "gatescore_ok_today": True,
                "gatescore_recent_enough": True,
                "gatescore_age_days": 0,
                "min_samples_ok_today": True,
                "contract_semantics_level": "FULL_LIVE_ELIGIBLE",
                "nvda_blockg_ready": nvda_ready,
                "spy_blockg_ready": False,
                "qqq_blockg_ready": False,
                "reasons_not_ready": ([] if nvda_ready else ["nvda_blockg_ready=false"]),
            }
        ),
        encoding="utf-8",
    )
    return p

def _write_nvda_stamp_ready(tmp_path: Path) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    p = tmp_path / "nvda_live_ready_stamp.json"
    p.write_text(
        json.dumps({"ts_utc": "2025-01-01T00:00:00Z", "as_of_date": today, "nvda_live_ready": True}),
        encoding="utf-8",
    )
    return p



def test_ib_chokepoint_blocks_live_when_blockg_not_ready(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HAT_IS_PAPER", "0")  # live
    stamp = _write_nvda_stamp_ready(tmp_path)
    monkeypatch.setenv("HAT_LIVE_READY_STAMP_PATH", str(stamp))
    token = tmp_path / "live_arm_nvda.json"     token.write_text(json.dumps({"symbol":"NVDA","as_of_date":"2099-01-01","armed":True}) + "\n", encoding="utf-8")     monkeypatch.setenv("HAT_LIVE_ARM_TOKEN_PATH", str(token))
    p = _write_status(tmp_path, nvda_ready=False)
    monkeypatch.setenv("HAT_BLOCKG_STATUS_PATH", str(p))

    ib = _IB()
    c = _C("NVDA")
    o = _O()

    with pytest.raises(BlockGNotReady):
        ib_place_order_chokepoint(ib, c, o)

    assert ib.called is False


def test_ib_chokepoint_allows_live_when_blockg_ready(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HAT_IS_PAPER", "0")  # live
    stamp = _write_nvda_stamp_ready(tmp_path)
    monkeypatch.setenv("HAT_LIVE_READY_STAMP_PATH", str(stamp))
    p = _write_status(tmp_path, nvda_ready=True)
    monkeypatch.setenv("HAT_BLOCKG_STATUS_PATH", str(p))

    ib = _IB()
    c = _C("NVDA")
    o = _O()

    ib_place_order_chokepoint(ib, c, o)
    assert ib.called is True
