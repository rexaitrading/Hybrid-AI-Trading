from __future__ import annotations

import pytest

from hybrid_ai_trading.broker.ib_safe import ib_place_order_chokepoint

class _C:
    def __init__(self, symbol: str):
        self.symbol = symbol

class _IB:
    def __init__(self):
        self.called = False
    def placeOrder(self, *a, **k):
        self.called = True
        return None

def test_chokepoint_blocks_live_when_not_ready(monkeypatch):
    # Force "live"
    monkeypatch.setenv("HAT_IS_PAPER", "0")

    # Make Block-G always fail
    def _fail(sym: str, *a, **k):
        raise RuntimeError("BLOCKG_NOT_READY_TEST")
    monkeypatch.setattr("hybrid_ai_trading.broker.ib_safe.require_blockg_ready_for_live", _fail)

    ib = _IB()
    with pytest.raises(RuntimeError, match="BLOCKG_NOT_READY_TEST"):
        ib_place_order_chokepoint(ib, _C("NVDA"), object())

    assert ib.called is False
