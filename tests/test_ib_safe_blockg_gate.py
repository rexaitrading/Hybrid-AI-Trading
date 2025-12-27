from __future__ import annotations

import json
from pathlib import Path

import pytest

from hybrid_ai_trading.execution.blockg_enforce import BlockGNotReady
from hybrid_ai_trading.broker import ib_safe


class _IB:
    def __init__(self):
        self.called = False
    def placeOrder(self, *a, **k):
        self.called = True
        return None


def test_live_blocks_placeOrder_when_ibg_status_missing(monkeypatch):
    monkeypatch.setenv("HAT_IS_PAPER", "0")
    monkeypatch.setenv("HAT_IBG_STATUS_PATH", r"C:\__missing__\ibg.json")
    monkeypatch.setenv("HAT_SYMBOL", "NVDA")

    ib = _IB()
    with pytest.raises(BlockGNotReady):
        # call the chokepoint helper you have in ib_safe (adjust function name if needed)
        ib_safe.ib_place_order_chokepoint(ib, 0, type("C", (), {"symbol":"NVDA"})(), object())
    assert ib.called is False


def test_live_blocks_placeOrder_when_status_stale(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HAT_IS_PAPER", "0")
    monkeypatch.setenv("HAT_SYMBOL", "NVDA")

    p = tmp_path / "ibg_status.json"
    p.write_text(json.dumps({"timestamp": "2000-01-01T00:00:00+00:00", "portUp": True}), encoding="utf-8")
    monkeypatch.setenv("HAT_IBG_STATUS_PATH", str(p))

    ib = _IB()
    with pytest.raises(BlockGNotReady):
        ib_safe.ib_place_order_chokepoint(ib, 0, type("C", (), {"symbol":"NVDA"})(), object())
    assert ib.called is False
