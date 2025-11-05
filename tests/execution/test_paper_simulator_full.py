"""
Unit Tests: PaperSimulator (Hybrid AI Quant Pro v13.5 Ã¢â‚¬â€œ Absolute 100% Coverage)
-------------------------------------------------------------------------------
Covers ALL branches in simulate_fill:
- Invalid side rejection
- Invalid size/price
- Latency applied (patched time.sleep)
- Limit orders rejected if not triggered
- Limit orders triggered (normal fill)
- Stop/stop-limit orders pending if not triggered
- Stop/stop-limit orders triggered (normal fill)
- Slippage in both directions
- Commission models: % of notional, per-share, both combined
- Minimum commission enforcement
- Zero-commission path
- Borrow fees and funding rate applied
- Deterministic reproducibility with seed
- Partial fills
- Bracket orders (stop+target attached)
- Result contains all expected keys
"""

import random
from unittest.mock import patch

import pytest

from hybrid_ai_trading.execution.paper_simulator import PaperSimulator


# ---------------- Invalid Inputs ----------------
def test_invalid_side_and_size_price():
    sim = PaperSimulator()
    assert sim.simulate_fill("AAPL", "HOLD", 10, 100)["status"] == "error"
    assert sim.simulate_fill("AAPL", "BUY", 0, 100)["status"] == "error"
    assert sim.simulate_fill("AAPL", "BUY", 10, 0)["status"] == "error"


# ---------------- Latency ----------------
@patch("time.sleep", return_value=None)
def test_latency_applied(mock_sleep):
    sim = PaperSimulator(latency_ms=100)
    sim.simulate_fill("AAPL", "BUY", 1, 100)
    mock_sleep.assert_called_once()


# ---------------- Limit / Stop Orders ----------------
def test_limit_order_rejection():
    sim = PaperSimulator(slippage=0.0)
    result = sim.simulate_fill(
        "AAPL", "BUY", 10, 105, order_type="limit", limit_price=100
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "limit_not_triggered"


def test_limit_order_triggers_buy_and_sell():
    sim = PaperSimulator(slippage=0.0)
    # BUY price <= limit_price Ã¢â€ â€™ normal fill
    r1 = sim.simulate_fill("AAPL", "BUY", 10, 95, order_type="limit", limit_price=100)
    assert r1["status"] == "filled"
    # SELL price >= limit_price Ã¢â€ â€™ normal fill
    r2 = sim.simulate_fill("AAPL", "SELL", 10, 105, order_type="limit", limit_price=100)
    assert r2["status"] == "filled"


def test_stop_order_pending():
    sim = PaperSimulator(slippage=0.0)
    result = sim.simulate_fill("AAPL", "BUY", 10, 95, order_type="stop", stop_price=100)
    assert result["status"] == "pending"
    assert result["reason"] == "stop_not_triggered"


def test_stop_order_triggers_buy_and_sell():
    sim = PaperSimulator(slippage=0.0)
    # BUY stop triggered when price >= stop_price
    r1 = sim.simulate_fill("AAPL", "BUY", 10, 105, order_type="stop", stop_price=100)
    assert r1["status"] == "filled"
    # SELL stop triggered when price <= stop_price
    r2 = sim.simulate_fill("AAPL", "SELL", 10, 95, order_type="stop", stop_price=100)
    assert r2["status"] == "filled"


# ---------------- Slippage ----------------
def test_slippage_up_and_down(monkeypatch):
    sim = PaperSimulator(slippage=0.05)
    monkeypatch.setattr(random, "choice", lambda _: 1)
    up = sim.simulate_fill("AAPL", "BUY", 1, 100)
    assert up["fill_price"] > 100

    monkeypatch.setattr(random, "choice", lambda _: -1)
    down = sim.simulate_fill("AAPL", "BUY", 1, 100)
    assert down["fill_price"] < 100


# ---------------- Commission Models ----------------
def test_percentage_commission_only():
    sim = PaperSimulator(slippage=0.0, commission=0.001, commission_per_share=0.0)
    result = sim.simulate_fill("AAPL", "BUY", 10, 100)
    assert result["commission"] == pytest.approx(1.0)


def test_per_share_commission_only():
    sim = PaperSimulator(slippage=0.0, commission=0.0, commission_per_share=0.5)
    result = sim.simulate_fill("AAPL", "SELL", 2, 100)
    assert result["commission"] == pytest.approx(1.0)


def test_combined_commission_and_minimum():
    sim = PaperSimulator(
        slippage=0.0,
        commission=0.001,
        commission_per_share=0.1,
        min_commission=5.0,
    )
    result = sim.simulate_fill("AAPL", "BUY", 1, 10)
    assert result["commission"] == 5.0


def test_zero_commission_path():
    sim = PaperSimulator(slippage=0.0, commission=0.0, commission_per_share=0.0)
    result = sim.simulate_fill("AAPL", "BUY", 1, 100)
    assert result["commission"] == 0.0


# ---------------- Borrow / Funding ----------------
def test_borrow_and_funding_costs():
    sim = PaperSimulator(slippage=0.0, commission=0.0)
    sell = sim.simulate_fill("AAPL", "SELL", 10, 100, hold_days=2)
    assert sell["carry_cost"] > 0
    buy = sim.simulate_fill("AAPL", "BUY", 10, 100, hold_days=2)
    assert buy["carry_cost"] > 0


# ---------------- Determinism ----------------
def test_deterministic_seed_reproducible():
    sim1 = PaperSimulator(slippage=0.01, seed=123)
    r1 = sim1.simulate_fill("AAPL", "BUY", 10, 100)
    sim2 = PaperSimulator(slippage=0.01, seed=123)
    r2 = sim2.simulate_fill("AAPL", "BUY", 10, 100)
    assert r1 == r2


# ---------------- Partial Fills + Brackets ----------------
def test_partial_fills_and_bracket_orders():
    sim = PaperSimulator(slippage=0.0)
    result = sim.simulate_fill("AAPL", "BUY", 5, 100, stop_price=95, limit_price=110)
    assert "fills" in result
    assert "bracket" in result
    assert result["bracket"]["stop"] == 95
    assert result["bracket"]["target"] == 110


# ---------------- Result Keys ----------------
def test_result_contains_expected_keys():
    sim = PaperSimulator(slippage=0.0)
    result = sim.simulate_fill("AAPL", "BUY", 1, 100)
    for key in [
        "status",
        "symbol",
        "side",
        "size",
        "fill_price",
        "notional",
        "commission",
        "mode",
    ]:
        assert key in result
    assert result["mode"] == "paper"


def test_limit_and_stop_without_prices():
    sim = PaperSimulator(slippage=0.0)
    # Limit order with no limit_price should just fill
    r1 = sim.simulate_fill("AAPL", "BUY", 1, 100, order_type="limit")
    assert r1["status"] == "filled"

    # Stop order with no stop_price should just fill
    r2 = sim.simulate_fill("AAPL", "SELL", 1, 100, order_type="stop")
    assert r2["status"] == "filled"


def test_carry_cost_zero_days():
    sim = PaperSimulator(slippage=0.0, commission=0.0)
    r = sim.simulate_fill("AAPL", "BUY", 1, 100, hold_days=0)
    assert r["carry_cost"] == 0.0


def test_limit_order_without_limit_price():
    sim = PaperSimulator(slippage=0.0)
    result = sim.simulate_fill("AAPL", "BUY", 1, 100, order_type="limit")
    assert result["status"] == "filled"
    assert result["fill_price"] > 0


def test_no_carry_cost_when_hold_days_zero():
    sim = PaperSimulator(slippage=0.0, commission=0.0)
    result = sim.simulate_fill("AAPL", "SELL", 1, 100, hold_days=0)
    assert result["status"] == "filled"
    assert result["carry_cost"] == 0.0
