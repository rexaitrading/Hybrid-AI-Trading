import pytest
from hybrid_ai_trading.broker.ib_safe import ib_place_order_chokepoint


class DummyIB:
    def placeOrder(self, *args, **kwargs):
        raise AssertionError("placeOrder must NOT be called when BlockG is not ready")


class DummyContract:
    def __init__(self, symbol: str):
        self.symbol = symbol


class DummyOrder:
    pass


def test_ib_chokepoint_blocks_live_when_blockg_nonzero(monkeypatch):
    # Force LIVE mode
    monkeypatch.setenv("HAT_IS_PAPER", "0")

    ib = DummyIB()
    contract = DummyContract("NVDA")
    order = DummyOrder()

    # Closed day: Check-BlockGReady.ps1 returns exit=10 => must fail-closed BEFORE placeOrder
    with pytest.raises(Exception):
        ib_place_order_chokepoint(ib, 1, contract, order, ctx=None, meta={"symbol": "NVDA"})
