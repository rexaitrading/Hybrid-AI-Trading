import json
from pathlib import Path
import pytest

from hybrid_ai_trading.broker.ib_safe import ib_place_order_chokepoint
from hybrid_ai_trading.execution.blockg_errors import BlockGNotReady


class DummyIB:
    def placeOrder(self, *args, **kwargs):
        return {"ok": True, "args": args, "kwargs": kwargs}


class DummyContract:
    def __init__(self, symbol: str):
        self.symbol = symbol


class DummyOrder:
    pass


def test_ib_chokepoint_blocks_live_when_contract_not_ready(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    p = tmp_path / "blockg_status_stub.json"
    p.write_text(json.dumps({
        "as_of_date": "2099-01-01",
        "nvda_blockg_ready": False,
        "spy_blockg_ready": False,
        "qqq_blockg_ready": False,
        "reasons_not_ready": ["nvda_blockg_ready=false"],
    }), encoding="utf-8")

    monkeypatch.setenv("HAT_BLOCKG_STATUS_PATH", str(p))

    class LiveCtx:
        mode = "live"
        is_paper = False
        @property
        def is_live(self):
            return True

    ib = DummyIB()
    c = DummyContract("NVDA")
    o = DummyOrder()

    with pytest.raises(BlockGNotReady):
        ib_place_order_chokepoint(ib, c, o, ctx=LiveCtx(), meta={"symbol": "NVDA"})


def test_ib_chokepoint_allows_when_paper(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    p = tmp_path / "blockg_status_stub.json"
    p.write_text(json.dumps({
        "as_of_date": "2099-01-01",
        "nvda_blockg_ready": False,
        "spy_blockg_ready": False,
        "qqq_blockg_ready": False,
    }), encoding="utf-8")

    monkeypatch.setenv("HAT_BLOCKG_STATUS_PATH", str(p))

    class PaperCtx:
        mode = "paper"
        is_paper = True
        @property
        def is_live(self):
            return False

    ib = DummyIB()
    c = DummyContract("NVDA")
    o = DummyOrder()

    out = ib_place_order_chokepoint(ib, c, o, ctx=PaperCtx(), meta={"symbol": "NVDA"})
    assert out and out.get("ok") is True
