import pytest
from hybrid_ai_trading.broker.ib_safe import ib_place_order_chokepoint

class FakeIB:
    def __init__(self):
        self.called = False
    def placeOrder(self, *args, **kwargs):
        self.called = True
        return "SHOULD_NOT_BE_CALLED"

class Ctx:
    # LIVE triggers gate
    is_paper = False
    mode = "LIVE"
    market_closed_today = False
    session_name = "AFTER_CLOSE"
    market = "US"
    repo_root = r"C:\HATJ\HybridAITrading"

def test_live_session_gate_blocks_not_rth():
    ib = FakeIB()
    with pytest.raises(RuntimeError) as e:
        ib_place_order_chokepoint(ib, object(), object(), ctx=Ctx(), meta={"market":"US","symbol":"NVDA"})
    assert "LIVE BLOCKED" in str(e.value)
    assert ib.called is False
