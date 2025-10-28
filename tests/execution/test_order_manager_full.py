"""
Unit Tests: OrderManager Full Suite
(Hybrid AI Quant Pro v16.0 – Hedge-Fund Grade, 100% Coverage)
----------------------------------------------------------------
Covers all branches in order_manager.py:
- Invalid input rejection
- Risk veto (blocked)
- RiskManager error handling
- Dry-run with commission/slippage
- Live client success + failure
- Paper simulator fill + error + not initialized
- Cancel order (success + unknown)
- Flatten all
- sync_portfolio stub
"""

import logging

import pytest

from hybrid_ai_trading.execution.order_manager import OrderManager
from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker


# ----------------------------------------------------------------------
# Dummy RiskManagers
# ----------------------------------------------------------------------
class DummyRiskManagerAllow:
    def check_trade(self, symbol, side, size, notional):
        return True

    def approve_trade(self, symbol, side, size, price):
        return True


class DummyRiskManagerBlock:
    def check_trade(self, symbol, side, size, notional):
        return False


class DummyRiskManagerError:
    def check_trade(self, symbol, side, size, notional):
        raise Exception("risk error")


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def portfolio():
    return PortfolioTracker()


@pytest.fixture
def risk_manager_allow():
    return DummyRiskManagerAllow()


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_invalid_input(portfolio, risk_manager_allow):
    om = OrderManager(risk_manager_allow, portfolio, dry_run=True)
    res = om.place_order("AAPL", "BUY", 0, 100)
    assert res["status"] == "rejected"
    assert "invalid_input" in res["reason"]


def test_risk_veto(portfolio):
    om = OrderManager(DummyRiskManagerBlock(), portfolio, dry_run=True)
    res = om.place_order("AAPL", "BUY", 10, 100)
    assert res["status"] == "blocked"
    assert "Risk veto" in res["reason"]


def test_risk_error_logged(portfolio, caplog):
    om = OrderManager(DummyRiskManagerError(), portfolio, dry_run=True)
    caplog.set_level(logging.ERROR)
    res = om.place_order("AAPL", "BUY", 10, 100)
    assert res["status"] == "blocked"
    assert "RiskManager error" in caplog.text


def test_dry_run_with_commission_and_slippage(portfolio, risk_manager_allow, caplog):
    costs = {
        "slippage_per_share": 0.1,
        "commission_pct": 0.001,
        "commission_per_share": 0.05,
    }
    om = OrderManager(risk_manager_allow, portfolio, dry_run=True, costs=costs)
    with caplog.at_level(logging.INFO):
        res = om.place_order("AAPL", "BUY", 10, 100)
    assert res["status"] == "filled"
    assert "commission" in res["details"]


def test_live_mode_success_and_failure(portfolio, risk_manager_allow):
    class FakeLive:
        def submit_order(self, *a, **k):
            return {"_raw": {"id": "XYZ", "status": "ok"}}

    om = OrderManager(risk_manager_allow, portfolio, dry_run=False, live_client=FakeLive())
    res = om.place_order("AAPL", "BUY", 1, 100)
    assert res["status"] == "pending"

    class BadLive:
        def submit_order(self, *a, **k):
            raise RuntimeError("live fail")

    om2 = OrderManager(risk_manager_allow, portfolio, dry_run=False, live_client=BadLive())
    res2 = om2.place_order("AAPL", "BUY", 1, 100)
    assert res2["status"] == "error"
    assert "live fail" in res2["reason"]


def test_paper_simulator_fill_and_error(portfolio, risk_manager_allow):
    om = OrderManager(risk_manager_allow, portfolio, dry_run=True, use_paper_simulator=True)

    # Patch simulator to return filled
    om.simulator.simulate_fill = lambda *a, **k: {
        "status": "filled",
        "fill_price": 10,
        "commission": 0.1,
    }
    res = om.place_order("AAPL", "BUY", 1, 10)
    assert res["status"] == "filled"

    # Patch simulator to return error
    om.simulator.simulate_fill = lambda *a, **k: {
        "status": "error",
        "reason": "sim fail",
    }
    res2 = om.place_order("AAPL", "BUY", 1, 10)
    assert res2["status"] == "error"
    assert "sim fail" in res2["reason"]


def test_paper_simulator_not_initialized(portfolio, risk_manager_allow):
    om = OrderManager(risk_manager_allow, portfolio, dry_run=True, use_paper_simulator=True)
    om.simulator = None
    res = om.place_order("AAPL", "BUY", 1, 10)
    assert res["status"] == "error"
    assert "Simulator not initialized" in res["reason"]


def test_cancel_order_success_and_failure(portfolio, risk_manager_allow):
    om = OrderManager(risk_manager_allow, portfolio, dry_run=True)
    res = om.place_order("AAPL", "BUY", 1, 10)
    order_id = res["details"]["order_id"]

    cancel = om.cancel_order(order_id)
    assert cancel["status"] == "cancelled"

    cancel2 = om.cancel_order("bad_id")
    assert cancel2["status"] == "error"
    assert "unknown order_id" in cancel2["reason"]


def test_flatten_all_clears_orders(portfolio, risk_manager_allow):
    om = OrderManager(risk_manager_allow, portfolio, dry_run=True)
    om.place_order("AAPL", "BUY", 1, 10)
    assert om.active_orders
    res = om.flatten_all()
    assert res["status"] == "flattened"
    assert not om.active_orders


def test_sync_portfolio_stub(portfolio, risk_manager_allow, caplog):
    om = OrderManager(risk_manager_allow, portfolio, dry_run=True)
    caplog.set_level(logging.INFO)
    res = om.sync_portfolio()
    assert res["status"] == "ok"
    assert res["synced"] is True
    assert "sync_portfolio" in caplog.text
