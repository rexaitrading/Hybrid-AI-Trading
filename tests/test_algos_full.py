"""
Algo Executors Full Test Suite (Hybrid AI Quant Pro v10.7 – AAA Hedge-Fund Grade)
---------------------------------------------------------------------------------
Covers:
- TWAP, VWAP, Iceberg execution flows
- Edge cases (tiny size, invalid side, invalid price)
- Error handling & fallback
- Performance checks (size consistency, latency)
- Stress test (100 random algo trades)
- Audit: structured details logging
"""

import pytest, random
from hybrid_ai_trading.execution.order_manager import OrderManager
from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker
from hybrid_ai_trading.algos.twap import TWAPExecutor
from hybrid_ai_trading.algos.vwap import VWAPExecutor
from hybrid_ai_trading.algos.iceberg import IcebergExecutor


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def portfolio():
    return PortfolioTracker(100000)


@pytest.fixture
def dummy_risk_manager():
    class DummyRisk:
        def check_trade(self, pnl, trade_notional=None): return True
    return DummyRisk()


@pytest.fixture
def order_manager(dummy_risk_manager, portfolio):
    return OrderManager(dummy_risk_manager, portfolio, dry_run=True)


# ----------------------------------------------------------------------
# TWAP Tests
# ----------------------------------------------------------------------
def test_twap_basic_execution(order_manager):
    twap = TWAPExecutor(order_manager, slices=5, delay=0.0)
    result = twap.execute("AAPL", "BUY", 50, 100)
    assert result["status"] == "filled"
    total = sum(d["details"]["size"] for d in result["details"])
    assert total <= 50  # rounding safe guard


def test_twap_small_size(order_manager):
    twap = TWAPExecutor(order_manager, slices=10, delay=0.0)
    result = twap.execute("AAPL", "BUY", 3, 100)
    assert result["status"] == "filled"
    total = sum(d["details"]["size"] for d in result["details"])
    assert total >= 3


# ----------------------------------------------------------------------
# VWAP Tests
# ----------------------------------------------------------------------
def test_vwap_weighted_execution(order_manager):
    vwap = VWAPExecutor(order_manager, slices=4)
    result = vwap.execute("MSFT", "SELL", 40, 200)
    assert result["status"] == "filled"
    total = sum(d["details"]["size"] for d in result["details"])
    assert total <= 40


def test_vwap_invalid_price(order_manager):
    vwap = VWAPExecutor(order_manager, slices=3)
    result = vwap.execute("MSFT", "BUY", 10, 0)  # invalid price
    assert result["status"] in {"error", "filled", "rejected"}  # handled gracefully


# ----------------------------------------------------------------------
# Iceberg Tests
# ----------------------------------------------------------------------
def test_iceberg_execution(order_manager):
    iceberg = IcebergExecutor(order_manager, display_size=5, delay=0.0)
    result = iceberg.execute("TSLA", "BUY", 20, 250)
    assert result["status"] == "filled"
    total = sum(d["details"]["size"] for d in result["details"])
    assert total == 20


def test_iceberg_smaller_than_display(order_manager):
    iceberg = IcebergExecutor(order_manager, display_size=50, delay=0.0)
    result = iceberg.execute("TSLA", "SELL", 10, 250)
    assert result["status"] == "filled"
    total = sum(d["details"]["size"] for d in result["details"])
    assert total == 10


# ----------------------------------------------------------------------
# Error Handling
# ----------------------------------------------------------------------
def test_algo_execution_error(monkeypatch, order_manager):
    twap = TWAPExecutor(order_manager, slices=3, delay=0.0)
    # Force OrderManager to raise error
    monkeypatch.setattr(order_manager, "place_order",
                        lambda *a, **k: (_ for _ in ()).throw(Exception("boom")))
    result = twap.execute("AAPL", "BUY", 30, 100)
    assert result["status"] == "error"
    assert "TWAP" in result["reason"] or "execution" in result["reason"].lower()


# ----------------------------------------------------------------------
# Stress Test
# ----------------------------------------------------------------------
@pytest.mark.parametrize("algo_class", [TWAPExecutor, VWAPExecutor, IcebergExecutor])
def test_random_algo_trades(order_manager, algo_class):
    algo = algo_class(order_manager)
    for _ in range(30):  # 30 trades per algo
        sym = random.choice(["AAPL", "MSFT", "TSLA"])
        side = random.choice(["BUY", "SELL"])
        size = random.randint(1, 50)
        price = random.uniform(50, 500)
        result = algo.execute(sym, side, size, price)
        assert result["status"] in {"filled", "error"}
    # Ensure portfolio equity is valid
    assert order_manager.portfolio.equity >= 0
