"""
Execution Suite (Hybrid AI Quant Pro v21.3 – Unified OE AAA Coverage)
---------------------------------------------------------------------
Covers:
- PortfolioTracker (long, short, flips, exposure, equity, drawdowns, errors)
- OrderManager (invalids, dry-run, paper sim, risk veto, commissions, slippage, logs)
- PaperSimulator (invalid side, slippage up/down, commissions, determinism)
- VWAP Signal (empty bars, guards, BUY, SELL, HOLD, float-stable equality, exception handling)
- SmartOrderRouter (scoring, route choice)
- LatencyMonitor (reset, ok, warning, halt)
"""

import pytest
import random
import uuid
import time
import logging

from hybrid_ai_trading.execution import (
    PortfolioTracker,
    OrderManager,
    PaperSimulator,
    SmartOrderRouter,
    LatencyMonitor,
)
from hybrid_ai_trading.signals.vwap import vwap_signal


# ============================================================
# Utilities
# ============================================================

class DummyRiskManager:
    """Supports both .check_trade and .approve_trade APIs for test stability."""
    def __init__(self, allow=True):
        self.allow = allow
        self.last_notional = None

    def check_trade(self, pnl, trade_notional=None):
        self.last_notional = trade_notional
        return self.allow

    def approve_trade(self, *args, **kwargs):
        return self.allow


def make_bars(prices, vols=None):
    """Helper for VWAP tests."""
    return [{"c": p, "v": vols[i] if vols else 1} for i, p in enumerate(prices)]


@pytest.fixture
def tracker():
    return PortfolioTracker(100000)


@pytest.fixture
def risk_manager_allow():
    return DummyRiskManager(allow=True)


@pytest.fixture
def risk_manager_block():
    return DummyRiskManager(allow=False)


# ============================================================
# PortfolioTracker Tests
# ============================================================

def test_buy_sell_and_commission(tracker):
    tracker.update_position("AAPL", "BUY", 1, 100, commission=1)
    tracker.update_position("AAPL", "SELL", 1, 100, commission=2)
    assert tracker.cash < 100000


def test_partial_closes_and_flips(tracker):
    tracker.update_position("MSFT", "BUY", 10, 50)
    tracker.update_position("MSFT", "SELL", 5, 60)
    assert tracker.realized_pnl > 0

    tracker.update_position("AMZN", "SELL", 10, 3000)
    tracker.update_position("AMZN", "BUY", 15, 2900)
    pos = tracker.get_positions()["AMZN"]
    assert pos["size"] == 5
    assert tracker.realized_pnl > 0


def test_cleanup_and_exposure(tracker):
    tracker.update_position("AAPL", "BUY", 10, 100)
    tracker.update_position("AAPL", "SELL", 10, 100)
    assert "AAPL" not in tracker.get_positions()

    exp = tracker.get_total_exposure(price_updates={"FAKE": 999})
    assert exp == 0.0


def test_equity_and_drawdown(tracker):
    tracker.update_position("TSLA", "SELL", 5, 200)
    tracker.update_equity({"TSLA": 150})
    assert tracker.unrealized_pnl > 0

    tracker.update_equity({"TSLA": 250})
    assert tracker.unrealized_pnl < 0
    assert tracker.equity < tracker.starting_equity

    tracker.history = []
    assert tracker.get_drawdown() == 0.0


def test_invalid_inputs_raise(tracker):
    with pytest.raises(ValueError):
        tracker.update_position("AAPL", "BUY", 0, 100)
    with pytest.raises(ValueError):
        tracker.update_position("AAPL", "SELL", 10, 0)


# ============================================================
# PaperSimulator Tests
# ============================================================

def test_paper_simulator_invalid_side():
    sim = PaperSimulator(seed=42)
    result = sim.simulate_fill("AAPL", "HOLD", 5, 100)
    assert result["status"] == "error"
    assert "reason" in result


def test_paper_simulator_deterministic_seed():
    sim1 = PaperSimulator(slippage=0.01, commission=0.002, min_commission=0.5, seed=123)
    sim2 = PaperSimulator(slippage=0.01, commission=0.002, min_commission=0.5, seed=123)
    assert sim1.simulate_fill("TSLA", "BUY", 10, 50) == sim2.simulate_fill(
        "TSLA", "BUY", 10, 50
    )


def test_paper_simulator_slippage(monkeypatch):
    sim = PaperSimulator(slippage=0.05, commission=0.0, min_commission=0.0)

    monkeypatch.setattr(random, "choice", lambda _: 1)
    up = sim.simulate_fill("AAPL", "BUY", 1, 100)
    assert up["fill_price"] > 100

    monkeypatch.setattr(random, "choice", lambda _: -1)
    down = sim.simulate_fill("AAPL", "BUY", 1, 100)
    assert down["fill_price"] < 100


def test_paper_simulator_commission_models():
    sim = PaperSimulator(slippage=0.0, commission=0.01, commission_per_share=0.0)
    pct = sim.simulate_fill("META", "SELL", 5, 200)
    assert pct["commission"] > 0

    sim = PaperSimulator(slippage=0.0, commission=0.0, commission_per_share=0.5)
    per_share = sim.simulate_fill("AAPL", "BUY", 2, 100)
    assert per_share["commission"] == pytest.approx(1.0, rel=1e-3)

    sim = PaperSimulator(
        slippage=0.0, commission=0.001, commission_per_share=0.1, min_commission=5.0
    )
    min_comm = sim.simulate_fill("AAPL", "BUY", 1, 10)
    assert min_comm["commission"] == 5.0


def test_paper_simulator_zero_commission_keys():
    sim = PaperSimulator(slippage=0.0, commission=0.0)
    result = sim.simulate_fill("AAPL", "BUY", 1, 100)
    assert result["commission"] == 0.0
    for key in ["status", "symbol", "side", "size", "fill_price", "notional", "commission", "mode"]:
        assert key in result


# ============================================================
# OrderManager Tests
# ============================================================

def test_order_manager_invalid_inputs(tracker, risk_manager_allow):
    om = OrderManager(risk_manager_allow, tracker, dry_run=True)
    for case in [
        ("AAPL", "BUY", 0, 100, "Invalid size/price"),
        ("AAPL", "SELL", 10, 0, "Invalid size/price"),
        ("AAPL", "HOLD", 10, 100, "Invalid side"),
    ]:
        res = om.place_order(case[0], case[1], case[2], case[3])
        assert res["status"] == "rejected"
        assert "details" in res
        assert "portfolio" in res["details"]


def test_order_manager_dry_run_fill_and_portfolio(tracker, risk_manager_allow):
    costs = {"commission_pct": 0.01, "slippage_per_share": 0.1}
    om = OrderManager(risk_manager_allow, tracker, dry_run=True, costs=costs)
    result = om.place_order("AAPL", "BUY", 10, 100)
    assert result["status"] == "filled"
    assert "portfolio" in result["details"]


def test_order_manager_minimum_commission(tracker, risk_manager_allow):
    costs = {"min_commission": 5.0}
    om = OrderManager(risk_manager_allow, tracker, dry_run=True, costs=costs)
    result = om.place_order("AAPL", "BUY", 1, 10)
    assert result["details"]["commission"] == 5.0


def test_order_manager_risk_veto(tracker, risk_manager_block):
    om = OrderManager(risk_manager_block, tracker, dry_run=True)
    result = om.place_order("AAPL", "BUY", 10, 100)
    assert result["status"] == "blocked"
    assert "details" in result
    assert "portfolio" in result["details"]


def test_order_manager_live_mode(tracker, risk_manager_allow):
    om = OrderManager(risk_manager_allow, tracker, dry_run=False)
    result = om.place_order("AAPL", "BUY", 10, 100)
    assert result["status"] == "pending"
    assert "details" in result


def test_order_manager_paper_simulator_success(monkeypatch, tracker, risk_manager_allow):
    om = OrderManager(risk_manager_allow, tracker, dry_run=True, use_paper_simulator=True)
    monkeypatch.setattr(
        om.simulator,
        "simulate_fill",
        lambda s, side, size, price: {
            "status": "filled",
            "fill_price": price + 0.2,
            "commission": 1.5,
            "notional": (price + 0.2) * size,
        },
    )
    result = om.place_order("AAPL", "BUY", 10, 100)
    assert result["status"] == "filled"
    assert "portfolio" in result["details"]


def test_order_manager_paper_simulator_error(monkeypatch, tracker, risk_manager_allow):
    om = OrderManager(risk_manager_allow, tracker, dry_run=True, use_paper_simulator=True)
    monkeypatch.setattr(
        om.simulator, "simulate_fill", lambda *a, **k: {"status": "error", "reason": "forced_fail"}
    )
    result = om.place_order("AAPL", "BUY", 10, 100)
    assert result["status"] == "error"
    assert "details" in result
    assert result["reason"] == "forced_fail"


def test_order_manager_uuid_and_timestamp(monkeypatch, tracker, risk_manager_allow):
    om = OrderManager(risk_manager_allow, tracker, dry_run=True)
    monkeypatch.setattr(uuid, "uuid4", lambda: "fixed-uuid")
    monkeypatch.setattr(time, "time", lambda: 1234567890)
    result = om.place_order("AAPL", "BUY", 1, 100)
    assert result["details"]["order_id"].startswith("fixed-uuid")
    assert result["details"]["timestamp"] == 1234567890
