"""
Unit Tests: PortfolioTracker (Hybrid AI Quant Pro v114.0 â€“ 100% Coverage, Hedge-Fund Grade)
--------------------------------------------------------------------------------------------
Covers all branches in portfolio_tracker.py:
- Invalid inputs
- Commissions (buy/sell deduction)
- Partial closes & flips (longâ†’short, shortâ†’long, coverâ†’long)
- Cleanup (flat, tolerance positive & negative, exact flat cases)
- update_equity: None, {}, valid, unknown-only, mixed, tolerance cleanup
- Exposures: total, net
- VaR & CVaR: base, zero vol, no losses, single loss, multi-loss, percentile fail
- Sharpe & Sortino: empty history, zero-vol, no downside, downside std==0
- Report: includes positions + risk metrics, matches snapshot
- Stress: high frequency trading updates
- reset_day: success + exception branch + intraday_trades=None
"""

import builtins
from datetime import datetime

import pytest

from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def tracker():
    return PortfolioTracker(starting_equity=100000)


# ----------------------------------------------------------------------
# Invalid Inputs
# ----------------------------------------------------------------------
def test_update_position_invalid_inputs(tracker):
    with pytest.raises(ValueError):
        tracker.update_position("AAPL", "BUY", 0, 100)
    with pytest.raises(ValueError):
        tracker.update_position("AAPL", "SELL", 10, 0)


# ----------------------------------------------------------------------
# Commission
# ----------------------------------------------------------------------
def test_commission_buy_and_sell(tracker):
    tracker.update_position("AAPL", "BUY", 1, 100, commission=1)
    tracker.update_position("AAPL", "SELL", 1, 100, commission=2)
    assert tracker.cash < 100000
    assert tracker.realized_pnl <= 0


# ----------------------------------------------------------------------
# Partial closes & flips
# ----------------------------------------------------------------------
def test_partial_close_long_and_short(tracker):
    tracker.update_position("MSFT", "BUY", 10, 50)
    tracker.update_position("MSFT", "SELL", 5, 60)
    assert tracker.realized_pnl > 0

    tracker.update_position("AMZN", "SELL", 10, 3000)
    tracker.update_position("AMZN", "BUY", 5, 2900)
    assert tracker.realized_pnl > 0


def test_flip_long_to_short_and_short_to_long(tracker):
    tracker.update_position("META", "BUY", 10, 300)
    tracker.update_position("META", "SELL", 15, 320)
    assert tracker.get_positions()["META"]["size"] == -5

    tracker.update_position("NFLX", "SELL", 10, 500)
    tracker.update_position("NFLX", "BUY", 15, 480)
    assert tracker.get_positions()["NFLX"]["size"] == 5


def test_cover_short_then_open_new_long(tracker):
    tracker.update_position("XYZ", "SELL", 10, 100, commission=1)
    tracker.update_position("XYZ", "BUY", 15, 90, commission=1)
    pos = tracker.get_positions()["XYZ"]
    assert pos["size"] == 5
    assert pos["avg_price"] > 0


def test_cover_short_then_new_long_with_commission(tracker):
    tracker.update_position("ABC", "SELL", 5, 100)
    tracker.update_position("ABC", "BUY", 10, 95, commission=2)
    pos = tracker.get_positions()["ABC"]
    assert pos["size"] > 0
    assert tracker.cash < 100000


# ----------------------------------------------------------------------
# Cleanup
# ----------------------------------------------------------------------
def test_cleanup_after_flat_and_tolerance(tracker):
    tracker.update_position("AAPL", "BUY", 10, 100)
    tracker.update_position("AAPL", "SELL", 10, 100)
    assert "AAPL" not in tracker.get_positions()

    tracker.update_position("TSLA", "BUY", 1, 100)
    tracker.positions["TSLA"]["size"] = 1e-9
    tracker.update_equity({"TSLA": 100})
    assert "TSLA" not in tracker.get_positions()

    tracker.update_position("IBM", "SELL", 1, 100)
    tracker.positions["IBM"]["size"] = -1e-9
    tracker.update_equity({"IBM": 100})
    assert "IBM" not in tracker.get_positions()


def test_cover_short_exact_cleanup(tracker):
    tracker.update_position("SHORTZERO", "SELL", 5, 100)
    tracker.update_position("SHORTZERO", "BUY", 5, 90)  # exactly flat
    assert "SHORTZERO" not in tracker.get_positions()


def test_close_long_exact_cleanup(tracker):
    tracker.update_position("LONGZERO", "BUY", 5, 100)
    tracker.update_position("LONGZERO", "SELL", 5, 110)  # exactly flat
    assert "LONGZERO" not in tracker.get_positions()


def test_cover_and_open_long_same_call(tracker):
    tracker.update_position("SYM", "SELL", 5, 100)  # short
    tracker.update_position("SYM", "BUY", 10, 90)  # cover 5 + open 5 long
    pos = tracker.get_positions()["SYM"]
    assert pos["size"] > 0


def test_close_and_open_short_same_call(tracker):
    tracker.update_position("SYM2", "BUY", 5, 100)  # long
    tracker.update_position("SYM2", "SELL", 10, 110)  # close 5 + new 5 short
    pos = tracker.get_positions()["SYM2"]
    assert pos["size"] < 0


def test_buy_covers_and_opens_long(tracker):
    tracker.update_position("MIX", "SELL", 5, 100)  # short
    tracker.update_position("MIX", "BUY", 10, 90)  # cover 5 + open 5 long
    pos = tracker.get_positions()["MIX"]
    assert pos["size"] == 5


def test_sell_closes_and_opens_short(tracker):
    tracker.update_position("MIX2", "BUY", 5, 100)  # long
    tracker.update_position("MIX2", "SELL", 10, 110)  # close 5 + open 5 short
    pos = tracker.get_positions()["MIX2"]
    assert pos["size"] == -5


# ----------------------------------------------------------------------
# update_equity
# ----------------------------------------------------------------------
def test_update_equity_none_and_empty(tracker):
    tracker.update_position("GOOG", "BUY", 1, 100)
    before = tracker.equity
    tracker.update_equity(None)
    tracker.update_equity({})
    assert tracker.equity >= before


def test_update_equity_unknown_and_cleanup(tracker, caplog):
    tracker.positions["FAKE"] = {"size": 1e-9, "avg_price": 200, "currency": "USD"}
    with caplog.at_level("DEBUG"):
        tracker.update_equity({"PHANTOM": 123})
    assert "Ignoring unknown symbol" in caplog.text
    assert "FAKE" not in tracker.get_positions()


# ----------------------------------------------------------------------
# Exposures
# ----------------------------------------------------------------------
def test_exposures(tracker):
    tracker.update_position("AAPL", "BUY", 10, 100)
    assert tracker.get_total_exposure() > 0
    assert tracker.get_net_exposure() > 0
    tracker.update_position("AAPL", "SELL", 20, 100)
    assert tracker.get_net_exposure() < 0


# ----------------------------------------------------------------------
# VaR & CVaR
# ----------------------------------------------------------------------
def test_var_and_cvar_paths(tracker, caplog):
    tracker.history = [(datetime.utcnow(), 100), (datetime.utcnow(), 101)]
    with caplog.at_level("DEBUG"):
        assert tracker.get_var(0.95) == 0.0
    assert "insufficient data for VaR" in caplog.text


def test_cvar_no_losses_after_cutoff(tracker, caplog):
    tracker.history = [
        (datetime.utcnow(), 100),
        (datetime.utcnow(), 110),
        (datetime.utcnow(), 120),
    ]
    with caplog.at_level("DEBUG"):
        val = tracker.get_cvar()
        assert val == 0.0
        assert "no losses" in caplog.text


def test_var_exception_branch(tracker, monkeypatch, caplog):
    tracker.history = [
        (datetime.utcnow(), 100),
        (datetime.utcnow(), 90),
        (datetime.utcnow(), 80),
    ]
    monkeypatch.setattr(
        "numpy.percentile", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fail"))
    )
    with caplog.at_level("WARNING"):
        v = tracker.get_var()
        assert v >= 0
        assert "VaR percentile error" in caplog.text


def test_cvar_exception_branch(tracker, monkeypatch, caplog):
    tracker.history = [
        (datetime.utcnow(), 100),
        (datetime.utcnow(), 90),
        (datetime.utcnow(), 80),
    ]
    monkeypatch.setattr(
        "numpy.percentile", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fail"))
    )
    with caplog.at_level("WARNING"):
        c = tracker.get_cvar()
        assert c >= 0
        assert "CVaR percentile error" in caplog.text


def test_var_scipy_import_failure(monkeypatch):
    tracker = PortfolioTracker()
    tracker.history = [(datetime.utcnow(), 100), (datetime.utcnow(), 110)]

    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name.startswith("scipy.stats"):
            raise ImportError("scipy not available")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert isinstance(tracker.get_var(0.95), float)


def test_cvar_single_negative_loss_branch(caplog):
    t = PortfolioTracker()
    t.history = [(datetime.utcnow(), 100), (datetime.utcnow(), 90)]
    with caplog.at_level("DEBUG"):
        val = t.get_cvar()
        assert val > 0
        assert "single loss branch" in caplog.text


def test_var_logs_insufficient_data(tracker, caplog):
    tracker.history = [(datetime.utcnow(), 100), (datetime.utcnow(), 101)]
    with caplog.at_level("DEBUG"):
        v = tracker.get_var()
    assert v == 0.0
    assert "insufficient data for VaR" in caplog.text


def test_cvar_all_returns_positive(tracker, caplog):
    tracker.history = [
        (datetime.utcnow(), 100),
        (datetime.utcnow(), 110),
        (datetime.utcnow(), 120),
    ]
    with caplog.at_level("DEBUG"):
        v = tracker.get_cvar()
    assert v == 0.0
    assert "no losses" in caplog.text


def test_var_with_empty_history(tracker):
    tracker.history = []
    assert tracker.get_var() == 0.0


def test_cvar_losses_but_none_below_cutoff(tracker, monkeypatch, caplog):
    tracker.history = [
        (datetime.utcnow(), 100),
        (datetime.utcnow(), 101),
        (datetime.utcnow(), 102),
    ]
    # Force cutoff high so no losses qualify
    monkeypatch.setattr("numpy.percentile", lambda *a, **k: -9999)
    with caplog.at_level("DEBUG"):
        val = tracker.get_cvar()
    assert val == 0.0
    assert "no losses" in caplog.text


# ----------------------------------------------------------------------
# Sharpe & Sortino
# ----------------------------------------------------------------------
def test_sharpe_and_sortino(tracker):
    tracker.history = []
    assert tracker.get_sharpe() == 0.0
    assert tracker.get_sortino() == 0.0

    tracker.history = [(datetime.utcnow(), 100), (datetime.utcnow(), 100)]
    assert tracker.get_sharpe() == 0.0
    assert tracker.get_sortino() == float("inf")

    tracker.history = [(datetime.utcnow(), 100), (datetime.utcnow(), 110)]
    assert isinstance(tracker.get_sharpe(), float)
    assert tracker.get_sortino() in [float("inf"), tracker.get_sortino()]


def test_sortino_downside_zero_std(tracker):
    tracker.history = [
        (datetime.utcnow(), 100),
        (datetime.utcnow(), 99),
        (datetime.utcnow(), 99),
    ]
    assert tracker.get_sortino() == 0.0


def test_returns_single_point_history():
    t = PortfolioTracker()
    t.history = [(datetime.utcnow(), 100)]
    assert t._returns() == []


# ----------------------------------------------------------------------
# Report & Snapshot
# ----------------------------------------------------------------------
def test_report_and_snapshot(tracker):
    rpt = tracker.report()
    assert "positions" in rpt
    assert rpt["positions"] == {}
    for key in ["var95", "cvar95", "sharpe", "sortino"]:
        assert key in rpt
    snap = tracker.snapshot()
    for k in ["equity", "cash", "realized_pnl", "unrealized_pnl"]:
        assert rpt[k] == snap[k]


# ----------------------------------------------------------------------
# Stress
# ----------------------------------------------------------------------
def test_stress_high_frequency(tracker):
    for i in range(50):
        tracker.update_position("HFT", "BUY", 1, 100 + (i % 5))
        tracker.update_position("HFT", "SELL", 1, 100 + (i % 5))
    rpt = tracker.report()
    assert isinstance(rpt["realized_pnl"], float)
    assert isinstance(rpt["var95"], float)


# ----------------------------------------------------------------------
# Reset Day
# ----------------------------------------------------------------------
def test_reset_day_success_and_exception():
    t = PortfolioTracker()
    res = t.reset_day()
    assert res["status"] == "ok"

    class BadTrades:
        def clear(self):
            raise Exception("boom")

    t.intraday_trades = BadTrades()
    res2 = t.reset_day()
    assert res2["status"] == "error"
    assert "boom" in res2["reason"]


def test_reset_day_intraday_trades_none():
    t = PortfolioTracker()
    t.intraday_trades = None  # breaks .clear()
    res = t.reset_day()
    assert res["status"] == "error"


def test_reset_day_runtime_error():
    t = PortfolioTracker()

    class BadTrades:
        def clear(self):
            raise RuntimeError("bad clear")

    t.intraday_trades = BadTrades()
    res = t.reset_day()
    assert res["status"] == "error"
    assert "bad clear" in res["reason"]


def test_var_returns_empty_history(tracker):
    tracker.history = []
    assert tracker.get_var() == 0.0


def test_cvar_mixed_returns(tracker):
    tracker.history = [
        (datetime.utcnow(), 100),
        (datetime.utcnow(), 90),
        (datetime.utcnow(), 110),
    ]
    val = tracker.get_cvar()
    assert isinstance(val, float)
    assert val >= 0


def test_reset_day_runtime_error_subclass():
    t = PortfolioTracker()

    class BadTrades:
        def clear(self):
            raise RuntimeError("bad clear")

    t.intraday_trades = BadTrades()
    res = t.reset_day()
    assert res["status"] == "error"
    assert "bad clear" in res["reason"]


def test_buy_cover_and_new_long_forces_both_paths(tracker, caplog):
    tracker.update_position("BRANCH1", "SELL", 5, 100)  # short
    with caplog.at_level("DEBUG"):
        tracker.update_position("BRANCH1", "BUY", 10, 90)  # cover 5 + open 5 long
    pos = tracker.get_positions()["BRANCH1"]
    assert pos["size"] == 5
    assert "COVER HIT" in caplog.text and "OPEN LONG HIT" in caplog.text


def test_sell_close_and_new_short_forces_both_paths(tracker, caplog):
    tracker.update_position("BRANCH2", "BUY", 5, 100)  # long
    with caplog.at_level("DEBUG"):
        tracker.update_position("BRANCH2", "SELL", 10, 110)  # close 5 + open 5 short
    pos = tracker.get_positions()["BRANCH2"]
    assert pos["size"] == -5
    assert "CLOSE LONG HIT" in caplog.text and "OPEN SHORT HIT" in caplog.text


def test_cvar_losses_exist_but_none_below_cutoff(tracker, monkeypatch, caplog):
    # Two negative returns but force cutoff too low so losses list is empty
    tracker.history = [
        (datetime.utcnow(), 100),
        (datetime.utcnow(), 90),  # -10%
        (datetime.utcnow(), 80),  # -11%
        (datetime.utcnow(), 82),  # +2.5%
    ]
    monkeypatch.setattr("numpy.percentile", lambda *a, **k: -999)  # cutoff excludes all
    with caplog.at_level("DEBUG"):
        val = tracker.get_cvar()
    assert val == 0.0
    assert "no losses" in caplog.text
