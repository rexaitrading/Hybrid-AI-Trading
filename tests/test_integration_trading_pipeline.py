"""
Integration Tests: Trading Pipeline (Hybrid AI Quant Pro v7.3 – Polished)
--------------------------------------------------------------------------
Covers full flow:
- OrderManager + RiskManager + PortfolioTracker working together
- Long/short trades and realized PnL
- Flips (short→long, long→short) and partial closes
- RiskManager veto on exposure, leverage, and daily loss
- Commission + slippage application
- Stress test: 200 random trades with blotter logging
- Final audit: no NaNs, equity ≥ 0, positions consistent
"""

import sys, os
import pytest
import random
import csv
import math
from datetime import datetime

# --- Setup trade blotter file ---
os.makedirs("tests/logs", exist_ok=True)
BLOTTER_FILE = f"tests/logs/trade_blotter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
with open(BLOTTER_FILE, mode="w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "step", "symbol", "side", "size", "price", "status",
        "realized_pnl", "equity", "cash"
    ])

# --- Ensure src/ is importable ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker
from hybrid_ai_trading.execution.order_manager import OrderManager
from hybrid_ai_trading.risk.risk_manager import RiskManager


@pytest.fixture
def setup_pipeline():
    """Reusable fixture for OrderManager + RiskManager + PortfolioTracker."""
    portfolio = PortfolioTracker(starting_equity=100000)
    risk = RiskManager(
        equity=100000,
        portfolio=portfolio,
        max_leverage=2.0,
        max_portfolio_exposure=0.5,
        daily_loss_limit=-0.05,
    )
    costs = {
        "commission_per_share": 0.01,
        "min_commission": 1.0,
        "slippage_per_share": 0.05,
    }
    om = OrderManager(risk, portfolio, dry_run=True, costs=costs)
    return om, risk, portfolio


# --- Core trade flows ---
def test_long_trade_pipeline(setup_pipeline):
    om, risk, portfolio = setup_pipeline
    om.place_order("AAPL", "BUY", 10, 100)
    om.place_order("AAPL", "SELL", 10, 110)
    report = portfolio.report()

    assert "AAPL" not in portfolio.get_positions()
    assert report["realized_pnl"] > 0
    assert report["cash"] > portfolio.starting_equity


def test_short_trade_pipeline(setup_pipeline):
    om, risk, portfolio = setup_pipeline
    om.place_order("TSLA", "SELL", 5, 200)
    om.place_order("TSLA", "BUY", 5, 150)
    report = portfolio.report()

    assert "TSLA" not in portfolio.get_positions()
    assert report["realized_pnl"] > 0
    assert report["cash"] > portfolio.starting_equity


def test_flip_long_to_short(setup_pipeline):
    om, risk, portfolio = setup_pipeline
    om.place_order("META", "BUY", 10, 300)
    om.place_order("META", "SELL", 15, 310)
    pos = portfolio.get_positions()["META"]

    assert pos["size"] == -5
    assert portfolio.realized_pnl >= 0


def test_flip_short_to_long(setup_pipeline):
    om, risk, portfolio = setup_pipeline
    om.place_order("MSFT", "SELL", 10, 250)
    om.place_order("MSFT", "BUY", 15, 240)
    pos = portfolio.get_positions()["MSFT"]

    assert pos["size"] == 5
    assert portfolio.realized_pnl > 0


# --- Risk Manager vetoes ---
def test_risk_veto_exposure_limit(setup_pipeline):
    om, risk, portfolio = setup_pipeline
    risk.max_portfolio_exposure = 0.1
    result = om.place_order("AMZN", "BUY", 200, 100)
    assert result["status"] == "blocked"
    assert "AMZN" not in portfolio.get_positions()


def test_risk_veto_leverage_limit(setup_pipeline):
    om, risk, portfolio = setup_pipeline
    risk.max_leverage = 1.0
    result = om.place_order("NFLX", "BUY", 2000, 100)
    assert result["status"] == "blocked"
    assert "NFLX" not in portfolio.get_positions()


def test_risk_veto_daily_loss(setup_pipeline):
    om, risk, portfolio = setup_pipeline
    risk.daily_loss_limit = -0.01

    om.place_order("AAPL", "BUY", 10, 100)
    portfolio.update_equity({"AAPL": 50})
    assert not risk.check_trade(-2000)


# --- Commission & slippage ---
def test_commission_and_slippage_applied(setup_pipeline):
    om, risk, portfolio = setup_pipeline
    result = om.place_order("AAPL", "BUY", 10, 100)
    details = result["details"]

    assert details["commission"] >= 1.0
    assert details["price"] != 100


# --- Stress test ---
def test_stress_random_trading_pipeline(setup_pipeline):
    om, risk, portfolio = setup_pipeline
    symbols = ["AAPL", "TSLA", "MSFT", "AMZN", "META"]

    for i in range(200):
        symbol = random.choice(symbols)
        side = random.choice(["BUY", "SELL"])
        size = random.randint(1, 20)
        price = random.uniform(50, 500)

        result = om.place_order(symbol, side, size, price)
        status = result["status"]

        # Append trade to blotter
        with open(BLOTTER_FILE, mode="a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                i + 1, symbol, side, size, f"{price:.2f}", status,
                portfolio.realized_pnl, portfolio.equity, portfolio.cash
            ])

        assert status in ["filled", "blocked", "rejected"]

        if status == "filled":
            snapshot = result["details"]["portfolio"]
            assert snapshot["equity"] >= 0
            assert isinstance(snapshot["cash"], float)
            assert not math.isnan(snapshot["realized_pnl"])
            assert not math.isnan(snapshot["unrealized_pnl"])

    final_report = portfolio.report()
    assert final_report["equity"] >= 0
    assert isinstance(final_report["cash"], float)
