from __future__ import annotations

import json
from pathlib import Path

import pytest

from hybrid_ai_trading.broker.ib_safe import ib_place_order_chokepoint
from hybrid_ai_trading.execution.blockg_enforce import BlockGNotReady


class _IBStub:
    def __init__(self):
        self.calls = []

    def placeOrder(self, *a, **k):
        self.calls.append((a, k))
        return {"ok": True}


class _ContractStub:
    def __init__(self, symbol: str):
        self.symbol = symbol


class _OrderStub:
    pass


def test_ib_safe_blocks_live_nvda_when_blockg_not_ready(tmp_path: Path, monkeypatch):
    # Force live intent
    monkeypatch.setenv("HAT_IS_PAPER", "0")
    monkeypatch.delenv("HAT_LIVE_DISABLED", raising=False)
    monkeypatch.delenv("HAT_CONFIRM_LIVE", raising=False)

    # Provide a status file that denies NVDA
    st = {
        "as_of_date": "2025-12-29",
        "nvda_blockg_ready": False,
        "spy_blockg_ready": False,
        "qqq_blockg_ready": False,
        "reasons_not_ready": ["unit_test"],
    }
    p = tmp_path / "blockg_status_stub.json"
    p.write_text(json.dumps(st), encoding="utf-8")
    monkeypatch.setenv("HAT_BLOCKG_STATUS_PATH", str(p))

    ib = _IBStub()
    c = _ContractStub("NVDA")
    o = _OrderStub()

    with pytest.raises((BlockGNotReady, RuntimeError)):
        ib_place_order_chokepoint(ib, c, o, meta={"symbol": "NVDA"})
    assert ib.calls == []
