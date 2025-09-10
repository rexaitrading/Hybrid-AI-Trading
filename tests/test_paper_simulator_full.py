"""
Unit Tests: PaperSimulator (Hybrid AI Quant Pro v9.5 - 100% Coverage)
---------------------------------------------------------------------
Covers:
- Invalid side rejection
- Deterministic reproducibility with seed
- Slippage applied (both directions)
- Commission models: % of notional, per-share, both combined
- Minimum commission enforcement
- Zero-commission path
- Return dictionary keys (including 'mode')
"""

import pytest
import random
from hybrid_ai_trading.execution.paper_simulator import PaperSimulator


def test_invalid_side_rejected():
    sim = PaperSimulator()
    result = sim.simulate_fill("AAPL", "HOLD", 10, 100)
    assert result["status"] == "error"
    assert result["reason"] == "invalid_side"


def test_deterministic_seed_reproducible():
    # Using the same seed → reproducible results
    sim1 = PaperSimulator(slippage=0.01, seed=123)
    r1 = sim1.simulate_fill("AAPL", "BUY", 10, 100)

    sim2 = PaperSimulator(slippage=0.01, seed=123)
    r2 = sim2.simulate_fill("AAPL", "BUY", 10, 100)

    assert r1 == r2


def test_slippage_applied_both_directions(monkeypatch):
    sim = PaperSimulator(slippage=0.05)

    # Force random.choice to return +1 (up slippage)
    monkeypatch.setattr(random, "choice", lambda _: 1)
    up = sim.simulate_fill("AAPL", "BUY", 1, 100)
    assert up["fill_price"] > 100

    # Force random.choice to return -1 (down slippage)
    monkeypatch.setattr(random, "choice", lambda _: -1)
    down = sim.simulate_fill("AAPL", "BUY", 1, 100)
    assert down["fill_price"] < 100


def test_percentage_commission_only():
    sim = PaperSimulator(slippage=0.0, commission=0.001, commission_per_share=0.0)
    result = sim.simulate_fill("AAPL", "BUY", 10, 100)
    assert result["commission"] == pytest.approx(1.0)  # 0.1% of 1000


def test_per_share_commission_only():
    sim = PaperSimulator(slippage=0.0, commission=0.0, commission_per_share=0.5)
    result = sim.simulate_fill("AAPL", "SELL", 2, 100)
    assert result["commission"] == pytest.approx(1.0)  # 0.5 * 2


def test_combined_commission_and_minimum():
    sim = PaperSimulator(
        slippage=0.0,
        commission=0.001,
        commission_per_share=0.1,
        min_commission=5.0,
    )
    result = sim.simulate_fill("AAPL", "BUY", 1, 10)  # low notional → min kicks in
    assert result["commission"] == 5.0


def test_zero_commission_path():
    sim = PaperSimulator(slippage=0.0, commission=0.0, commission_per_share=0.0)
    result = sim.simulate_fill("AAPL", "BUY", 1, 100)
    assert result["commission"] == 0.0


def test_return_contains_mode_and_keys():
    sim = PaperSimulator(slippage=0.0, commission=0.001)
    result = sim.simulate_fill("AAPL", "BUY", 1, 100)
    # Ensure dictionary contains all expected keys
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
