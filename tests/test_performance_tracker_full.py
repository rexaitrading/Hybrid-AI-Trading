"""
Unit Tests: PerformanceTracker (Hybrid AI Quant Pro v6.5 – Absolute 100% Coverage)
---------------------------------------------------------------------------------
Covers all branches and logging paths in performance_tracker.py
"""

import pytest
from hybrid_ai_trading.performance_tracker import PerformanceTracker


# --- Init ---
def test_init_defaults_sets_window_and_lists():
    pt = PerformanceTracker(window=5)
    assert pt.window == 5
    assert pt.trades == []
    assert pt.equity_curve == []


# --- record_trade / record_equity ---
def test_record_trade_appends_and_trims_window(caplog):
    pt = PerformanceTracker(window=2)
    caplog.set_level("DEBUG")
    pt.record_trade(10)
    pt.record_trade(-5)
    pt.record_trade(20)  # oldest dropped
    assert pt.trades == [-5, 20]
    assert "Recorded trade" in caplog.text

def test_record_equity_appends_and_trims_window(caplog):
    pt = PerformanceTracker(window=2)
    caplog.set_level("DEBUG")
    pt.record_equity(100)
    pt.record_equity(110)
    pt.record_equity(120)  # oldest dropped
    assert pt.equity_curve == [110, 120]
    assert "Recorded equity" in caplog.text


# --- win_rate ---
def test_win_rate_no_trades_logs_info(caplog):
    pt = PerformanceTracker()
    caplog.set_level("INFO")
    assert pt.win_rate() == 0.0
    assert "No trades" in caplog.text

def test_win_rate_mixed_trades_fractional():
    pt = PerformanceTracker()
    pt.record_trade(10)
    pt.record_trade(-5)
    pt.record_trade(15)
    assert 0 < pt.win_rate() < 1

def test_win_rate_all_wins_and_all_losses():
    pt = PerformanceTracker()
    pt.record_trade(5)
    pt.record_trade(15)
    assert pt.win_rate() == 1.0

    pt2 = PerformanceTracker()
    pt2.record_trade(-5)
    pt2.record_trade(-15)
    assert pt2.win_rate() == 0.0


# --- payoff_ratio ---
def test_payoff_ratio_no_trades_and_no_losses_logs_info(caplog):
    pt = PerformanceTracker()
    caplog.set_level("INFO")
    assert pt.payoff_ratio() == 0.0
    assert "No trades" in caplog.text

    pt2 = PerformanceTracker()
    pt2.record_trade(10)
    pt2.record_trade(20)
    caplog.set_level("INFO")
    assert pt2.payoff_ratio() == 0.0
    assert "No losses" in caplog.text

def test_payoff_ratio_valid_case_and_only_losses():
    pt = PerformanceTracker()
    pt.record_trade(10)
    pt.record_trade(-5)
    pt.record_trade(20)
    assert pt.payoff_ratio() > 0

    pt2 = PerformanceTracker()
    pt2.record_trade(-5)
    pt2.record_trade(-10)
    assert pt2.payoff_ratio() == 0.0


# --- sharpe_ratio ---
def test_sharpe_ratio_not_enough_trades_logs_info(caplog):
    pt = PerformanceTracker()
    pt.record_trade(10)
    caplog.set_level("INFO")
    assert pt.sharpe_ratio() == 0.0
    assert "Not enough trades" in caplog.text

def test_sharpe_ratio_valid_and_zero_vol():
    pt = PerformanceTracker()
    pt.record_trade(10)
    pt.record_trade(20)
    assert pt.sharpe_ratio() != 0.0

    pt2 = PerformanceTracker()
    pt2.record_trade(5)
    pt2.record_trade(5)
    assert pt2.sharpe_ratio() == 0.0

def test_sharpe_ratio_exception(monkeypatch, caplog):
    pt = PerformanceTracker()
    pt.record_trade(1)
    pt.record_trade(2)

    # Force mean() to raise
    monkeypatch.setattr("hybrid_ai_trading.performance_tracker.mean",
                        lambda x: (_ for _ in ()).throw(Exception("boom")))
    caplog.set_level("ERROR")
    assert pt.sharpe_ratio() == 0.0
    assert "Sharpe calc error" in caplog.text


# --- sortino_ratio ---
def test_sortino_ratio_not_enough_trades_logs_info(caplog):
    pt = PerformanceTracker()
    pt.record_trade(10)
    caplog.set_level("INFO")
    assert pt.sortino_ratio() == 0.0
    assert "Not enough trades" in caplog.text

def test_sortino_ratio_with_downside_and_empty_downside(caplog):
    pt = PerformanceTracker()
    pt.record_trade(10)
    pt.record_trade(-5)
    assert pt.sortino_ratio() != 0.0

    pt2 = PerformanceTracker()
    pt2.record_trade(5)
    pt2.record_trade(10)
    caplog.set_level("WARNING")
    assert pt2.sortino_ratio() != 0.0
    assert "No downside trades" in caplog.text

def test_sortino_ratio_single_negative_trade_and_downside_zero(caplog):
    pt = PerformanceTracker()
    pt.record_trade(-5)
    pt.record_trade(15)  # single downside
    caplog.set_level("WARNING")
    assert pt.sortino_ratio() != 0.0
    assert "fallback" in caplog.text

    pt2 = PerformanceTracker()
    pt2.record_trade(-5)
    pt2.record_trade(-5)  # downside stdev = 0
    caplog.set_level("WARNING")
    assert pt2.sortino_ratio() != 0.0
    assert "Downside stdev=0" in caplog.text

def test_sortino_ratio_exception(monkeypatch, caplog):
    pt = PerformanceTracker()
    pt.record_trade(-5)
    pt.record_trade(-10)

    # Force pstdev() to raise
    monkeypatch.setattr("hybrid_ai_trading.performance_tracker.pstdev",
                        lambda x: (_ for _ in ()).throw(Exception("bad pstdev")))
    caplog.set_level("ERROR")
    assert pt.sortino_ratio() == 0.0
    assert "Sortino calc error" in caplog.text


# --- equity + drawdown ---
def test_get_equity_curve_and_copy():
    pt = PerformanceTracker()
    assert pt.get_equity_curve() == []

    pt.record_equity(100)
    pt.record_equity(110)
    curve = pt.get_equity_curve()
    assert curve[-1] == 110
    assert curve is not pt.equity_curve

def test_get_drawdown_empty_and_flat_and_drop(caplog):
    pt = PerformanceTracker()
    caplog.set_level("INFO")
    assert pt.get_drawdown() == 0.0
    assert "No equity data" in caplog.text

    pt.record_equity(100)
    pt.record_equity(120)
    assert pt.get_drawdown() == 0.0

    pt.record_equity(80)
    assert pt.get_drawdown() > 0

def test_get_drawdown_with_zero_peak():
    pt = PerformanceTracker()
    pt.equity_curve = [0, 0, 0]
    pt.record_equity(0)
    assert pt.get_drawdown() == 0.0

def test_sortino_ratio_downside_zero_branch(caplog):
    """Explicitly cover branch when downside stdev == 0 (78->82)."""
    pt = PerformanceTracker()
    pt.record_trade(-5)
    pt.record_trade(-5)  # downside trades constant → stdev=0
    caplog.set_level("WARNING")
    ratio = pt.sortino_ratio()
    assert ratio != 0.0
    assert "Downside stdev=0" in caplog.text
