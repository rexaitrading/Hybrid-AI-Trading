import pytest

from hybrid_ai_trading.execution.blockg_enforce import BlockGNotReady
import hybrid_ai_trading.brokers.ib_adapter as ibmod
import hybrid_ai_trading.broker.ib_safe as ibsafe
class DummyIB:
    def placeOrder(self, contract, order):
        raise AssertionError("placeOrder should not be called when Block-G blocks live")

    def sleep(self, *_args, **_kwargs):
        return None


def test_ib_adapter_place_order_blocks_live(monkeypatch):
    monkeypatch.setenv("HAT_IS_PAPER", "0")
    # Force enforcement to raise
    def fake_require(symbol):
        raise BlockGNotReady("blocked")

    monkeypatch.setattr(ibsafe, "require_blockg_ready_for_live", fake_require)

    # Build adapter instance without connecting
    a = ibmod.IBAdapter.__new__(ibmod.IBAdapter)
    a.ib = DummyIB()
    a.is_paper = False  # LIVE

    with pytest.raises(BlockGNotReady):
        a.place_order(symbol="NVDA", side="BUY", qty=1.0, order_type="MARKET")
