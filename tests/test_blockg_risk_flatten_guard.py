from __future__ import annotations

import json
from pathlib import Path

import pytest

from hybrid_ai_trading.execution.blockg_enforce import BlockGNotReady
from hybrid_ai_trading.utils.risk import _flatten_one


class _C:
    def __init__(self, symbol: str):
        self.symbol = symbol


class _P:
    def __init__(self, symbol: str, position: int):
        self.contract = _C(symbol)
        self.position = position


class _IB:
    def __init__(self):
        self.called = False

    def placeOrder(self, *a, **k):
        self.called = True
        return None


def test_risk_flatten_blocks_live_when_not_ready(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HAT_IS_PAPER", "0")

    status = {
        "nvda_blockg_ready": False,
        "spy_blockg_ready": False,
        "qqq_blockg_ready": False,
        "reasons_not_ready": ["nvda_blockg_ready=false"],
    }
    p = tmp_path / "blockg_status_stub.json"
    p.write_text(json.dumps(status), encoding="utf-8")
    monkeypatch.setenv("HAT_BLOCKG_STATUS_PATH", str(p))

    ib = _IB()
    pos = _P("NVDA", 10)

    with pytest.raises(BlockGNotReady):
        _flatten_one(ib, pos)

    assert ib.called is False


def test_risk_flatten_allows_paper(monkeypatch):
    monkeypatch.setenv("HAT_IS_PAPER", "1")
    ib = _IB()
    pos = _P("NVDA", 10)
    _flatten_one(ib, pos)
