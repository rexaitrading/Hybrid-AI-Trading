"""
Unit Tests: IcebergExecutor (Hybrid AI Quant Pro v2.1 – Hedge Fund Grade, AAA Coverage)
--------------------------------------------------------------------------------------
Covers all branches in iceberg.py:
- Multi-slice execution (size > display_size)
- Exact single-slice execution
- Broker + fill_price normalization
- Exception handling branch
- Delay > 0 path (monkeypatched sleep)
- Display size normalization (<1 → forced to 1)
- Zero/negative size edge case
"""

import pytest
from hybrid_ai_trading.algos.iceberg import IcebergExecutor


# ----------------------------------------------------------------------
# Dummy OrderManager
# ----------------------------------------------------------------------
class DummyOrderManager:
    def __init__(self, fail_at: int = None, broker: str = "alpaca"):
        self.calls = []
        self.fail_at = fail_at
        self.broker = broker

    def place_order(self, symbol, side, size, price):
        self.calls.append((symbol, side, size, price))
        if self.fail_at and len(self.calls) == self.fail_at:
            raise Exception("forced fail")
        return {
            "status": "filled",
            "fill_price": price - 0.5,
            "broker": self.broker,
        }


@pytest.fixture
def dummy_manager():
    return DummyOrderManager()


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_multi_slice_execution(monkeypatch, dummy_manager):
    """Splits into multiple slices (12 → 5+5+2)."""
    iceberg = IcebergExecutor(dummy_manager, display_size=5, delay=0.1)
    monkeypatch.setattr("time.sleep", lambda *_: None)  # avoid real sleep
    res = iceberg.execute("AAPL", "BUY", 12, 100.0)
    assert res["status"] == "filled"
    assert res["algo"] == "Iceberg"
    assert len(res["details"]) == 3
    assert all("status" in d for d in res["details"])


def test_exact_single_slice(dummy_manager):
    """Executes exactly one slice."""
    iceberg = IcebergExecutor(dummy_manager, display_size=10, delay=0)
    res = iceberg.execute("AAPL", "SELL", 10, 150.0)
    assert res["status"] == "filled"
    assert len(res["details"]) == 1
    assert res["details"][0]["size"] == 10


def test_broker_and_fill_price():
    """Normalizes broker + fill_price from OrderManager."""
    mgr = DummyOrderManager(broker="ibkr")
    iceberg = IcebergExecutor(mgr, display_size=3)
    res = iceberg.execute("TSLA", "BUY", 6, 200.0)
    first = res["details"][0]
    assert first["broker"] == "ibkr"
    assert first["price"] == 199.5  # 200 - 0.5


def test_exception_branch(monkeypatch):
    """Forces exception on 2nd slice → returns error."""
    mgr = DummyOrderManager(fail_at=2)
    iceberg = IcebergExecutor(mgr, display_size=2)
    monkeypatch.setattr("time.sleep", lambda *_: None)
    res = iceberg.execute("MSFT", "BUY", 5, 300.0)
    assert res["status"] == "error"
    assert "Iceberg execution failure" in res["reason"]
    assert res["algo"] == "Iceberg"


def test_delay_branch(monkeypatch, dummy_manager):
    """Covers delay > 0 path (patched sleep)."""
    iceberg = IcebergExecutor(dummy_manager, display_size=2, delay=0.05)
    called = {}
    monkeypatch.setattr("time.sleep", lambda t: called.update({"slept": t}))
    iceberg.execute("NVDA", "SELL", 4, 400.0)
    assert "slept" in called and called["slept"] == 0.05


def test_display_size_normalization(dummy_manager):
    """Display size <1 normalized to 1."""
    iceberg = IcebergExecutor(dummy_manager, display_size=0)
    res = iceberg.execute("META", "BUY", 2, 50.0)
    assert all(d["size"] == 1 for d in res["details"])


def test_zero_or_negative_size(dummy_manager):
    """Zero size returns immediately with no slices."""
    iceberg = IcebergExecutor(dummy_manager, display_size=5)
    res = iceberg.execute("AAPL", "BUY", 0, 100.0)
    assert res["status"] == "filled"
    assert res["details"] == []
