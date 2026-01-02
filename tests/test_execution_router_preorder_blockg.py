from __future__ import annotations

import pytest

from hybrid_ai_trading.execution.brokers import IBKRClient, BrokerError


class _IBStub:
    def __init__(self):
        self.place_called = False
    def connect(self, *a, **k):
        return True
    def sleep(self, *a, **k):
        return None
    def placeOrder(self, *a, **k):
        self.place_called = True
        raise AssertionError("IB placeOrder should NOT be called when Block-G fails pre-order")


def test_ibkrclient_blocks_before_order_when_live(monkeypatch):
    # Force "live" intent via meta + env
    monkeypatch.setenv("HAT_IS_PAPER", "0")

    # Make ensure_symbol_blockg_ready fail-closed
    import hybrid_ai_trading.execution.brokers as m
    def _boom(*a, **k):
        raise RuntimeError("BLOCKG_FAIL_CLOSED")
    monkeypatch.setattr(m, "ensure_symbol_blockg_ready", _boom, raising=True)

    # Replace IB class with stub (avoid real ib_insync)
    monkeypatch.setattr(m, "IB", lambda: _IBStub(), raising=False)
    monkeypatch.setattr(m, "Stock", lambda *a, **k: object(), raising=False)
    monkeypatch.setattr(m, "MarketOrder", lambda *a, **k: object(), raising=False)
    monkeypatch.setattr(m, "LimitOrder", lambda *a, **k: object(), raising=False)

    c = m.IBKRClient()
    with pytest.raises(RuntimeError, match="BLOCKG_FAIL_CLOSED"):
        c.submit_order("NVDA", "BUY", 1, order_type="MARKET", meta={"is_paper": False})

