"""
Unit Tests: PortfolioTracker (Hybrid AI Quant Pro v73.0 - Absolute 100% Coverage)
---------------------------------------------------------------------------------
Covers every branch and edge case:
- Long & short opens, closes, flips
- Partial closes (long/short)
- Commission handling (buy & sell)
- Realized & unrealized PnL
- Cleanup when position flat (math.isclose)
- Equity updates: None, {}, price_updates, short gains & losses
- Exposure: None fallback, {}, invalid symbol, matching symbol
- Report() with/without positions, with drawdowns
- Invalid inputs (size <=0 or price <=0)
- Drawdown edge case (empty history, peak=0)
"""

import pytest
from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker


# --- Fixtures ---
@pytest.fixture
def tracker():
    return PortfolioTracker(starting_equity=100000)


# --- Basic Trading Flow ---
def test_buy_and_sell_commission(tracker):
    tracker.update_position("AAPL", "BUY", 1, 100, commission=1)
    assert tracker.cash < 100000
    tracker.update_position("AAPL", "SELL", 1, 100, commission=2)
    assert tracker.cash < 100000


def test_partial_close_long(tracker):
    tracker.update_position("MSFT", "BUY", 10, 50)
    tracker.update_position("MSFT", "SELL", 5, 60)
    assert tracker.realized_pnl == pytest.approx(50.0)


def test_partial_close_short(tracker):
    tracker.update_position("AMZN", "SELL", 10, 3000)
    tracker.update_position("AMZN", "BUY", 5, 2900)
    assert tracker.realized_pnl == pytest.approx(500.0)


def test_flip_long_to_short(tracker):
    tracker.update_position("META", "BUY", 10, 300)
    tracker.update_position("META", "SELL", 15, 320)
    pos = tracker.get_positions()["META"]
    assert pos["size"] == -5
    assert tracker.realized_pnl > 0


def test_flip_short_to_long(tracker):
    tracker.update_position("NFLX", "SELL", 10, 500)
    tracker.update_position("NFLX", "BUY", 15, 480)
    pos = tracker.get_positions()["NFLX"]
    assert pos["size"] == 5
    assert tracker.realized_pnl > 0


def test_cleanup_after_flat(tracker):
    tracker.update_position("AAPL", "BUY", 10, 100)
    tracker.update_position("AAPL", "SELL", 10, 100)  # exactly flat
    assert "AAPL" not in tracker.get_positions()


# --- Exposure ---
def test_get_total_exposure_empty_positions(tracker):
    assert tracker.get_total_exposure() == 0.0


def test_get_total_exposure_with_price_updates(tracker):
    tracker.update_position("AAPL", "BUY", 10, 100)
    exposure = tracker.get_total_exposure(price_updates={"AAPL": 120})
    assert exposure == pytest.approx(1200.0)


def test_get_total_exposure_without_price_updates_multiple_symbols(tracker):
    tracker.update_position("AAPL", "BUY", 10, 100)
    tracker.update_position("MSFT", "BUY", 20, 50)
    exposure = tracker.get_total_exposure()  # fallback to avg_price
    assert exposure == pytest.approx(2000.0)


def test_exposure_empty_dict_vs_none(tracker):
    tracker.update_position("AAPL", "BUY", 5, 200)
    exp_none = tracker.get_total_exposure(None)   # fallback branch
    exp_empty = tracker.get_total_exposure({})    # explicit empty dict
    assert exp_none > 0
    assert exp_empty == 0.0


def test_exposure_dict_with_invalid_symbol(tracker):
    tracker.update_position("AAPL", "BUY", 1, 100)
    exposure = tracker.get_total_exposure(price_updates={"FAKE": 999})
    assert exposure == 0.0


def test_get_total_exposure_with_matching_symbol(tracker):
    """Covers explicit dict branch with a real symbol."""
    tracker.update_position("AAPL", "BUY", 2, 100)
    result = tracker.get_total_exposure(price_updates={"AAPL": 200})
    assert result == pytest.approx(400.0)  # 2 × 200


# --- Equity & Drawdowns ---
def test_update_equity_empty_vs_none(tracker):
    tracker.update_position("AAPL", "BUY", 1, 100)
    tracker.update_equity(None)
    eq_none = tracker.equity
    tracker.update_equity({})
    eq_empty = tracker.equity
    assert eq_none > 0
    assert eq_empty > 0


def test_update_equity_with_short_gain(tracker):
    tracker.update_position("TSLA", "SELL", 5, 200)
    tracker.update_equity({"TSLA": 150})  # price falls → unrealized gain
    assert tracker.unrealized_pnl > 0


def test_update_equity_with_short_loss(tracker):
    """Force branch for unrealized loss when short price rises."""
    tracker.update_position("TSLA", "SELL", 5, 200)
    tracker.update_equity({"TSLA": 250})  # price rises → loss
    assert tracker.unrealized_pnl < 0
    assert tracker.equity < tracker.starting_equity


def test_report_no_positions(tracker):
    report = tracker.report()
    assert report["total_exposure"] == 0.0
    assert report["drawdown_pct"] == 0.0


def test_report_with_positions_and_drawdown(tracker):
    tracker.update_position("AAPL", "BUY", 10, 100)
    tracker.update_equity({"AAPL": 50})
    report = tracker.report()
    assert report["total_exposure"] > 0
    assert report["drawdown_pct"] > 0


def test_drawdown_with_empty_history(tracker):
    tracker.history = []
    assert tracker.get_drawdown() == 0.0


def test_drawdown_with_zero_peak():
    pt = PortfolioTracker(starting_equity=0)
    pt.equity = 0
    assert pt.get_drawdown() == 0.0


# --- Error Handling ---
def test_update_position_invalid_inputs(tracker):
    with pytest.raises(ValueError):
        tracker.update_position("AAPL", "BUY", 0, 100)
    with pytest.raises(ValueError):
        tracker.update_position("AAPL", "SELL", 10, 0)

def test_update_equity_force_short_loss_branch(tracker):
    """Force unrealized loss for a short position (branch 71->87)."""
    # Open short and DO NOT close it
    tracker.update_position("TSLA", "SELL", 5, 200)
    tracker.update_equity({"TSLA": 250})  # price up → loss
    assert tracker.unrealized_pnl < 0
    assert tracker.equity < tracker.starting_equity


def test_get_total_exposure_force_matching_branch(tracker):
    """Force branch where price_updates has a matching symbol (branch 105->99)."""
    tracker.update_position("AAPL", "BUY", 2, 100)
    exposure = tracker.get_total_exposure(price_updates={"AAPL": 150})
    assert exposure == pytest.approx(300.0)  # 2 × 150
