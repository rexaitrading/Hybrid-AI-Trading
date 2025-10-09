"""
Unit Tests: TWAP Executor (Hybrid AI Quant Pro v2.2 – 100% Coverage)
--------------------------------------------------------------------
Covers ALL branches in twap.py:
- Multi-slice execution
- Slice normalization (slices < 1 forced to 1)
- Size < slices → slice_size = 1
- Delay > 0 branch (monkeypatched sleep)
- Invalid parameters (size <= 0, price <= 0)
- Normalization of status=ok → filled
- Exception branch when place_order raises
"""

import pytest

import hybrid_ai_trading.algos.twap as twap


# ----------------------------------------------------------------------
# Dummy OrderManager
# ----------------------------------------------------------------------
class DummyOrderManager:
    def __init__(self, fail_at=None, status="filled"):
        self.calls = []
        self.fail_at = fail_at
        self.status = status

    def place_order(self, symbol, side, size, price):
        self.calls.append((symbol, side, size, price))
        if self.fail_at and len(self.calls) == self.fail_at:
            raise Exception("forced fail")
        return {
            "status": self.status,
            "fill_price": price - 0.1,
            "broker": "sim",
        }


@pytest.fixture
def manager():
    return DummyOrderManager()


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_multi_slice_execution(monkeypatch, manager):
    """Splits order into multiple slices with delay patched out."""
    ex = twap.TWAPExecutor(manager, slices=3, delay=0.1)
    monkeypatch.setattr("time.sleep", lambda *_: None)  # skip real sleep
    res = ex.execute("AAPL", "BUY", 9, 100)
    assert res["status"] == "filled"
    assert res["algo"] == "TWAP"
    assert len(res["details"]) == 3
    assert all("status" in d for d in res["details"])


def test_slice_normalization_and_size_lt_slices(manager):
    """Covers slices < 1 → forced to 1, and size < slices → slice_size=1."""
    ex1 = twap.TWAPExecutor(manager, slices=0)  # normalized to 1
    res1 = ex1.execute("TSLA", "SELL", 5, 200)
    assert len(res1["details"]) == 1

    ex2 = twap.TWAPExecutor(manager, slices=10)  # size < slices
    res2 = ex2.execute("TSLA", "SELL", 3, 200)
    assert all(d["size"] == 1 for d in res2["details"])


def test_delay_branch(monkeypatch, manager):
    """Ensures delay path triggers patched sleep."""
    ex = twap.TWAPExecutor(manager, slices=2, delay=0.05)
    called = {}
    monkeypatch.setattr("time.sleep", lambda t: called.update({"slept": t}))
    ex.execute("NVDA", "BUY", 4, 150)
    assert called["slept"] == 0.05


def test_invalid_parameters(manager):
    """Invalid params (size<=0 or price<=0) return error."""
    ex = twap.TWAPExecutor(manager, slices=2)
    assert ex.execute("AMZN", "BUY", 0, 100)["status"] == "error"
    assert ex.execute("AMZN", "BUY", 5, 0)["status"] == "error"


def test_status_normalization_ok(manager):
    """status=ok from broker normalized to filled."""
    ex = twap.TWAPExecutor(DummyOrderManager(status="ok"), slices=1)
    res = ex.execute("META", "SELL", 5, 50)
    assert res["details"][0]["status"] == "filled"


def test_exception_branch(monkeypatch):
    """place_order raises → error returned with partial results."""
    mgr = DummyOrderManager(fail_at=2)
    ex = twap.TWAPExecutor(mgr, slices=3)
    monkeypatch.setattr("time.sleep", lambda *_: None)
    res = ex.execute("GOOG", "BUY", 6, 1200)
    assert res["status"] == "error"
    assert "TWAP execution failure" in res["reason"]
    assert len(res["details"]) == 1  # only first slice succeeded


def test_exception_first_slice(monkeypatch):
    """Covers branch where first slice fails immediately."""
    mgr = DummyOrderManager(fail_at=1)
    ex = twap.TWAPExecutor(mgr, slices=3)
    monkeypatch.setattr("time.sleep", lambda *_: None)
    res = ex.execute("NFLX", "BUY", 6, 500)
    assert res["status"] == "error"
    assert "slice 1" in res["reason"]
    assert res["details"] == []  # no successful slices


def test_twap_executor_first_slice_exception(monkeypatch):
    """Covers branch: failure on the first slice triggers error return."""
    from hybrid_ai_trading.algos.twap import TWAPExecutor

    class FailingManager:
        def place_order(self, *a, **k):
            raise Exception("first slice boom")

    twap = TWAPExecutor(FailingManager(), slices=3, delay=0)
    res = twap.execute("AAPL", "BUY", 9, 100.0)
    assert res["status"] == "error"
    assert (
        "first slice" in res["reason"].lower()
        or "TWAP execution failure" in res["reason"]
    )
    assert res["algo"] == "TWAP"
    assert res["details"] == []  # nothing filled before failure
