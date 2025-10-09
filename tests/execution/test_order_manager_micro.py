"""
Unit Tests: OrderManager Micro Patches
(Hybrid AI Quant Pro v16.0 – Hedge-Fund Grade, 100% Coverage)
----------------------------------------------------------------
Covers missing branches in order_manager.py:
- Legacy risk_manager.check_trade fallback
- Live client error handling
- Simulator error return
- Cancel order unknown ID
- Flatten all
- sync_portfolio stub
"""

import pytest

from hybrid_ai_trading.execution.order_manager import OrderManager
from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def portfolio():
    return PortfolioTracker()


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_risk_check_legacy_signature(portfolio):
    """Covers legacy check_trade(pnl, trade_notional) fallback branch."""

    class LegacyRisk:
        def check_trade(self, pnl, trade_notional=None):
            return True

    om = OrderManager(LegacyRisk(), portfolio, dry_run=True)
    res = om.place_order("AAPL", "BUY", 1, 100)
    assert res["status"] == "filled"


def test_live_client_error(portfolio):
    """Covers live client error handling branch."""

    class BadLive:
        def submit_order(self, *a, **k):
            raise RuntimeError("boom")

    om = OrderManager(
        risk_manager=None, portfolio=portfolio, dry_run=False, live_client=BadLive()
    )
    res = om.place_order("AAPL", "BUY", 1, 100)
    assert res["status"] == "error"
    assert "boom" in res["reason"]


def test_paper_simulator_error(portfolio):
    """Covers simulator returning error dict."""

    class DummyRisk:
        def check_trade(self, *a, **k):
            return True

    om = OrderManager(DummyRisk(), portfolio, dry_run=True, use_paper_simulator=True)
    om.simulator.simulate_fill = lambda *a, **k: {
        "status": "error",
        "reason": "sim fail",
    }
    res = om.place_order("AAPL", "BUY", 1, 10)
    assert res["status"] == "error"
    assert "sim fail" in res["reason"]


def test_cancel_order_unknown_id(portfolio):
    """Covers cancel_order unknown ID branch."""

    class DummyRisk:
        def check_trade(self, *a, **k):
            return True

    om = OrderManager(DummyRisk(), portfolio, dry_run=True)
    res = om.cancel_order("does_not_exist")
    assert res["status"] == "error"
    assert "unknown order_id" in res["reason"]


def test_flatten_all_clears_orders(portfolio):
    """Covers flatten_all emergency clear branch."""

    class DummyRisk:
        def check_trade(self, *a, **k):
            return True

    om = OrderManager(DummyRisk(), portfolio, dry_run=True)
    om.place_order("AAPL", "BUY", 1, 100)
    assert om.active_orders
    res = om.flatten_all()
    assert res["status"] == "flattened"
    assert not om.active_orders


def test_sync_portfolio_stub(portfolio):
    """Covers sync_portfolio stub branch."""

    class DummyRisk:
        def check_trade(self, *a, **k):
            return True

    om = OrderManager(DummyRisk(), portfolio, dry_run=True)
    res = om.sync_portfolio()
    assert res["status"] == "ok"
    assert res["synced"] is True
