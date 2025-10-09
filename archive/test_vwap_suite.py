"""
Unit Tests: VWAP Executor (Hybrid AI Quant Pro v46.0 – 100% Coverage)
----------------------------------------------------------------------
Covers:
- BUY flow
- SELL flow
- HOLD branch
- Invalid price
- Invalid size
- Unexpected signal handling
- Exception handling
"""

import logging
import pytest
from hybrid_ai_trading.algos.vwap_executor import VWAPExecutor


class DummyOrderManager:
    def place_order(self, *args, **kwargs):
        return {"status": "filled"}


@pytest.fixture
def dummy_order_manager():
    return DummyOrderManager()


def test_vwap_executor_buy_flow(dummy_order_manager):
    vwap = VWAPExecutor(dummy_order_manager)
    result = vwap.execute("AAPL", "BUY", 10, 200)
    assert result["status"] == "filled"

# … (rest of the test file here, full content as I gave above)
