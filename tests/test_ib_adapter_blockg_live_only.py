import types
import pytest

import hybrid_ai_trading.brokers.ib_adapter as mod

class DummyTrade:
    def __init__(self):
        self.order = types.SimpleNamespace(orderId=123)
        self.orderStatus = types.SimpleNamespace(status="Submitted", filled=0, avgFillPrice=0.0)

def test_ib_adapter_blocks_nvda_only_when_live(monkeypatch):
    monkeypatch.setenv("HAT_RUN_MODE", "live")
    monkeypatch.setenv("IBKR_LIVE", "0")

    # Block-G fails hard
    def boom(sym: str):
        raise RuntimeError("BLOCKG_FAIL")
    monkeypatch.setattr(mod, "ensure_symbol_blockg_ready", boom)

    # Patch IB/Order/Contract to avoid ib_insync dependency
    monkeypatch.setattr(mod, "Stock", lambda *a, **k: types.SimpleNamespace(symbol=a[0]))
    monkeypatch.setattr(mod, "MarketOrder", lambda *a, **k: object())
    monkeypatch.setattr(mod, "LimitOrder", lambda *a, **k: object())

    a = mod.IBAdapter.__new__(mod.IBAdapter)
    a.ib = types.SimpleNamespace(placeOrder=lambda *a, **k: (_ for _ in ()).throw(AssertionError("placeOrder must not be called")),
                                 sleep=lambda *a, **k: None)

    with pytest.raises(RuntimeError, match="BLOCKG_FAIL"):
        a.place_order("NVDA", "BUY", 1.0, order_type="MARKET")

def test_ib_adapter_allows_nvda_when_not_live(monkeypatch):
    monkeypatch.delenv("HAT_RUN_MODE", raising=False)
    monkeypatch.setenv("IBKR_LIVE", "0")

    # Even if Block-G would fail, it must not be invoked
    def boom(sym: str):
        raise RuntimeError("BLOCKG_FAIL")
    monkeypatch.setattr(mod, "ensure_symbol_blockg_ready", boom)

    monkeypatch.setattr(mod, "Stock", lambda *a, **k: types.SimpleNamespace(symbol=a[0]))
    monkeypatch.setattr(mod, "MarketOrder", lambda *a, **k: object())
    monkeypatch.setattr(mod, "LimitOrder", lambda *a, **k: object())

    a = mod.IBAdapter.__new__(mod.IBAdapter)
    a.ib = types.SimpleNamespace(placeOrder=lambda *a, **k: DummyTrade(),
                                 sleep=lambda *a, **k: None)

    order_id, meta = a.place_order("NVDA", "BUY", 1.0, order_type="MARKET")
    assert order_id == 123
    assert meta["status"] == "Submitted"