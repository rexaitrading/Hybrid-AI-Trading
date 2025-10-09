"""
Unit Tests: TWAPExecutor (Hybrid AI Quant Pro v2.3 – Hedge Fund Grade, AAA Coverage)
------------------------------------------------------------------------------------
Covers ALL branches in twap_executor.py:
- Multi-slice execution
- Single-slice normalization (slices < 1 → forced to 1)
- Invalid parameters (size <= 0, price <= 0)
- Exception handling branch
- Delay > 0 path (monkeypatched sleep)
"""

import pytest

from hybrid_ai_trading.algos.twap_executor import TWAPExecutor


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
            "status": "ok",  # normalized to "filled"
            "fill_price": price - 0.25,
            "broker": self.broker,
        }


@pytest.fixture
def dummy_manager():
    return DummyOrderManager()


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_multi_slice_execution(monkeypatch, dummy_manager):
    """Splits into multiple slices."""
    twap = TWAPExecutor(dummy_manager, slices=3, delay=0.1)
    monkeypatch.setattr("time.sleep", lambda *_: None)
    res = twap.execute("AAPL", "BUY", 9, 100.0)
    assert res["status"] == "filled"
    assert len(res["details"]) == 3
    assert all(d["status"] == "filled" for d in res["details"])


def test_single_slice_normalization(dummy_manager):
    """Forces slices < 1 → normalized to 1."""
    twap = TWAPExecutor(dummy_manager, slices=0)
    res = twap.execute("TSLA", "SELL", 5, 200.0)
    assert res["status"] == "filled"
    assert len(res["details"]) == 1
    assert res["details"][0]["size"] == 5  # entire order in one slice


def test_invalid_parameters(dummy_manager, caplog):
    """Covers invalid params (size <=0, price <=0)."""
    twap = TWAPExecutor(dummy_manager, slices=3)
    caplog.set_level("WARNING")
    res1 = twap.execute("MSFT", "BUY", 0, 100.0)
    res2 = twap.execute("MSFT", "BUY", 10, 0.0)
    assert res1["status"] == "error" and "invalid" in res1["reason"]
    assert res2["status"] == "error" and "invalid" in res2["reason"]
    assert "Invalid parameters" in caplog.text


def test_exception_handling(monkeypatch):
    """Forces failure on 2nd slice → returns error."""
    mgr = DummyOrderManager(fail_at=2)
    twap = TWAPExecutor(mgr, slices=3, delay=0.1)
    monkeypatch.setattr("time.sleep", lambda *_: None)
    res = twap.execute("NVDA", "BUY", 6, 300.0)
    assert res["status"] == "error"
    assert "TWAP execution failure" in res["reason"]
    assert res["algo"] == "TWAP"


def test_delay_branch(monkeypatch, dummy_manager):
    """Covers delay > 0 path."""
    twap = TWAPExecutor(dummy_manager, slices=2, delay=0.05)
    called = {}
    monkeypatch.setattr("time.sleep", lambda t: called.update({"slept": t}))
    res = twap.execute("META", "SELL", 4, 50.0)
    assert res["status"] == "filled"
    assert "slept" in called and called["slept"] == 0.05
