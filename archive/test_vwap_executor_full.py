"""
Unit Tests: VWAP Executor
(Hybrid AI Quant Pro v46.3 – Hedge Fund Grade, AAA Coverage)
=================================================================
Covers ALL branches in vwap_executor.py:
- BUY → filled
- SELL → filled
- HOLD → rejected
- Unexpected signal → error
- Exception path when vwap_signal raises
"""

import pytest

from hybrid_ai_trading.algos import get_algo_executor

# Load VWAPExecutor class via orchestrator (avoids circular import issues)
VWAPExecutor = get_algo_executor("VWAP")


# ----------------------------------------------------------------------
# Dummy OrderManager
# ----------------------------------------------------------------------
class DummyOrderManager:
    """Minimal stub to satisfy VWAPExecutor constructor."""

    def place_order(self, *args, **kwargs):
        return {"status": "filled"}


@pytest.fixture
def executor():
    return VWAPExecutor(DummyOrderManager())


# ----------------------------------------------------------------------
# Happy-path flows
# ----------------------------------------------------------------------
def test_buy_and_sell_flows(monkeypatch, executor):
    """BUY/SELL signals map to status=filled."""
    import hybrid_ai_trading.algos.vwap_executor as vwap_executor

    monkeypatch.setattr(vwap_executor, "vwap_signal", lambda *_: "BUY")
    res_buy = executor.execute("AAPL", "BUY", 10, 100.0)
    assert res_buy["status"] == "filled"
    assert res_buy["details"][0]["signal"] == "BUY"

    monkeypatch.setattr(vwap_executor, "vwap_signal", lambda *_: "SELL")
    res_sell = executor.execute("TSLA", "SELL", 5, 200.0)
    assert res_sell["status"] == "filled"
    assert res_sell["details"][0]["signal"] == "SELL"


def test_hold_flow(monkeypatch, executor):
    """HOLD signal maps to rejected."""
    import hybrid_ai_trading.algos.vwap_executor as vwap_executor

    monkeypatch.setattr(vwap_executor, "vwap_signal", lambda *_: "HOLD")
    res = executor.execute("MSFT", "BUY", 1, 50.0)
    assert res["status"] == "rejected"
    assert res["details"][0]["signal"] == "HOLD"


def test_unexpected_signal(monkeypatch, executor):
    """Unexpected signal maps to error."""
    import hybrid_ai_trading.algos.vwap_executor as vwap_executor

    monkeypatch.setattr(vwap_executor, "vwap_signal", lambda *_: "WTF")
    res = executor.execute("NVDA", "SELL", 3, 400.0)
    assert res["status"] == "error"
    assert res["details"][0]["signal"] == "WTF"


# ----------------------------------------------------------------------
# Exception handling
# ----------------------------------------------------------------------
def test_exception_branch(monkeypatch, executor):
    """If vwap_signal raises, executor returns error."""
    import hybrid_ai_trading.algos.vwap_executor as vwap_executor

    def boom(*_):
        raise Exception("forced fail")

    monkeypatch.setattr(vwap_executor, "vwap_signal", boom)
    res = executor.execute("META", "BUY", 2, 75.0)
    assert res["status"] == "error"
    assert "forced fail" in res["reason"]
    assert res["algo"] == "VWAP"
