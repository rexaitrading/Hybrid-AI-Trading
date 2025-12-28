import json
import os
from pathlib import Path
import pytest

from hybrid_ai_trading.broker.ib_safe import ib_place_order_chokepoint

class FakeIB:
    def placeOrder(self, *a, **k):
        return {"ok": True}

class FakeContract:
    def __init__(self, symbol="NVDA"):
        self.symbol = symbol

class FakeOrder:
    pass

def test_live_order_denied_when_blockg_not_ready(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Force live mode
    monkeypatch.setenv("HAT_IS_PAPER", "0")

    # Write a deny blockg status file
    p = tmp_path / "blockg.json"
    p.write_text(json.dumps({"nvda_blockg_ready": False, "spy_blockg_ready": False, "qqq_blockg_ready": False}) + "\n", encoding="utf-8")
    monkeypatch.setenv("HAT_BLOCKG_STATUS_PATH", str(p))

    ib = FakeIB()
    contract = FakeContract("NVDA")
    order = FakeOrder()

    with pytest.raises(Exception):
        ib_place_order_chokepoint(ib, contract, order, ctx=None, meta={"symbol":"NVDA"})
