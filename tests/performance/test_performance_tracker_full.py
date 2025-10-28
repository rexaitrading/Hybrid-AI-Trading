"""
Unit Tests: PerformanceTracker (Hybrid AI Quant Pro v7.5 – AAA+ Coverage)
-----------------------------------------------------------------------
Covers ALL branches in performance_tracker.py:
- recorders (trade/equity/benchmark)
- win_rate/payoff/roi
- sharpe + sortino (valid, zero, exception, downside=0, no trades)
- calmar, omega
- alpha_beta (too few, valid, exception, zero-variance benchmark)
- drawdown + max drawdown + recovery
- snapshot()
- export_json (success + failure)
"""

import json

import pytest

from hybrid_ai_trading.performance_tracker import PerformanceTracker


# ----------------------------------------------------------------------
# Init & recorders
# ----------------------------------------------------------------------
def test_init_and_recorders(tmp_path, caplog):
    pt = PerformanceTracker(window=2)
    assert pt.window == 2

    caplog.set_level("DEBUG")
    pt.record_trade(10)
    pt.record_trade(-5)
    pt.record_trade(20)  # trims oldest
    assert pt.trades == [-5, 20]
    assert "Recorded trade" in caplog.text

    pt.record_equity(100)
    pt.record_equity(110)
    pt.record_equity(120)  # trims oldest
    assert pt.equity_curve == [110, 120]

    pt.record_benchmark(0.01)
    pt.record_benchmark(0.02)
    pt.record_benchmark(0.03)
    assert len(pt.benchmark) <= pt.window


# ----------------------------------------------------------------------
# Win rate & payoff
# ----------------------------------------------------------------------
def test_win_rate_and_payoff_ratio(caplog):
    pt = PerformanceTracker()
    caplog.set_level("INFO")
    assert pt.win_rate() == 0.0
    assert "No trades" in caplog.text

    pt.record_trade(10)
    pt.record_trade(-5)
    assert 0 < pt.win_rate() < 1

    pt2 = PerformanceTracker()
    pt2.record_trade(10)
    pt2.record_trade(20)
    assert pt2.payoff_ratio() == 0.0

    pt3 = PerformanceTracker()
    pt3.record_trade(10)
    pt3.record_trade(-5)
    assert pt3.payoff_ratio() > 0


# ----------------------------------------------------------------------
# ROI + Calmar + Omega
# ----------------------------------------------------------------------
def test_roi_and_calmar_and_omega():
    pt = PerformanceTracker()
    assert pt.roi() == 0.0  # no equity

    pt.equity_curve = [0, 0]
    assert pt.roi() == 0.0  # equity_curve[0]==0

    pt.equity_curve = [100, 120]
    assert pt.roi() == 0.2

    pt.max_drawdown = 0
    assert pt.calmar_ratio() == 0.0

    pt.max_drawdown = 0.1
    assert pt.calmar_ratio() > 0

    pt2 = PerformanceTracker()
    assert pt2.omega_ratio() == 0.0  # no trades
    pt2.record_trade(5)
    pt2.record_trade(-2)
    assert pt2.omega_ratio() >= 0.0


# ----------------------------------------------------------------------
# Sharpe ratio
# ----------------------------------------------------------------------
def test_sharpe_ratio_variants(monkeypatch, caplog):
    pt = PerformanceTracker()
    pt.record_trade(5)
    assert pt.sharpe_ratio() == 0.0  # not enough trades

    pt.record_trade(5)
    assert pt.sharpe_ratio() == 0.0  # std=0

    pt2 = PerformanceTracker()
    pt2.record_trade(10)
    pt2.record_trade(20)
    assert pt2.sharpe_ratio() > 0

    # Force mean() exception AFTER adding trades to bypass len<2 guard
    pt3 = PerformanceTracker()
    pt3.record_trade(10)
    pt3.record_trade(20)
    monkeypatch.setattr(
        "hybrid_ai_trading.performance_tracker.mean",
        lambda *_: (_ for _ in ()).throw(Exception("boom")),
    )
    caplog.set_level("ERROR")
    assert pt3.sharpe_ratio() == 0.0
    assert "Sharpe calc error" in caplog.text


# ----------------------------------------------------------------------
# Sortino ratio
# ----------------------------------------------------------------------
def test_sortino_ratio_variants(monkeypatch, caplog):
    pt = PerformanceTracker()
    pt.record_trade(5)
    assert pt.sortino_ratio() == 0.0  # not enough trades

    pt2 = PerformanceTracker()
    pt2.record_trade(10)
    pt2.record_trade(-5)
    assert pt2.sortino_ratio() != 0.0

    pt3 = PerformanceTracker()
    pt3.record_trade(5)
    pt3.record_trade(10)
    caplog.set_level("WARNING")
    pt3.sortino_ratio()
    assert "No downside trades" in caplog.text

    pt4 = PerformanceTracker()
    pt4.record_trade(-5)
    pt4.record_trade(-5)  # downside stdev=0
    caplog.set_level("WARNING")
    pt4.sortino_ratio()
    assert "Downside stdev=0" in caplog.text

    # Force pstdev exception
    pt5 = PerformanceTracker()
    pt5.record_trade(-5)
    pt5.record_trade(-10)
    monkeypatch.setattr(
        "hybrid_ai_trading.performance_tracker.pstdev",
        lambda *_: (_ for _ in ()).throw(Exception("bad pstdev")),
    )
    caplog.set_level("ERROR")
    assert pt5.sortino_ratio() == 0.0
    assert "Sortino calc error" in caplog.text


# ----------------------------------------------------------------------
# Alpha/Beta
# ----------------------------------------------------------------------
def test_alpha_beta_variants(monkeypatch, caplog):
    pt = PerformanceTracker()
    pt.trades = [1]
    pt.benchmark = [1]
    assert pt.alpha_beta() == {"alpha": 0.0, "beta": 0.0}

    pt.trades = [1, 2, 3]
    pt.benchmark = [1, 2, 3]
    res = pt.alpha_beta()
    assert "alpha" in res and "beta" in res

    # Force exception AFTER adding trades/benchmarks to bypass guard
    pt2 = PerformanceTracker()
    pt2.trades = [1, 2, 3]
    pt2.benchmark = [1, 2, 3]
    monkeypatch.setattr(
        "hybrid_ai_trading.performance_tracker.mean",
        lambda *_: (_ for _ in ()).throw(Exception("fail")),
    )
    caplog.set_level("ERROR")
    assert pt2.alpha_beta() == {"alpha": 0.0, "beta": 0.0}
    assert "Alpha/Beta calc error" in caplog.text


def test_alpha_beta_zero_variance_benchmark():
    """Benchmark with zero variance -> beta=0.0 path."""
    pt = PerformanceTracker()
    pt.trades = [1.0, 2.0, 3.0]
    pt.benchmark = [1.0, 1.0, 1.0]  # var_b = 0
    res = pt.alpha_beta()
    assert res == {
        "alpha": pt.trades
        and pytest.approx((sum(pt.trades) / len(pt.trades)) - (0.0 + 0.0 * 1.0), rel=1e-6)
        or 0.0,
        "beta": 0.0,
    }


# ----------------------------------------------------------------------
# Drawdown
# ----------------------------------------------------------------------
def test_drawdown_and_recovery_extra():
    pt = PerformanceTracker()
    assert pt.get_drawdown() == 0.0  # no equity

    # explicit equity_curve with peak=0 -> branch
    pt.equity_curve = [0]
    assert pt.get_drawdown() == 0.0

    pt.record_equity(100)
    pt.record_equity(120)
    pt.record_equity(80)
    assert pt.get_drawdown() > 0

    assert pt.get_max_drawdown() >= 0

    # drawdown_recovery_time may be None or int (including 0)
    val = pt.drawdown_recovery_time()
    assert val is None or isinstance(val, int)


# ----------------------------------------------------------------------
# Snapshot + Export
# ----------------------------------------------------------------------
def test_snapshot_and_export_json(tmp_path):
    pt = PerformanceTracker()
    pt.record_trade(10)
    pt.record_trade(-5)
    pt.record_equity(100)
    pt.record_equity(120)
    snap = pt.snapshot()
    assert isinstance(snap, dict)
    assert "win_rate" in snap

    path = tmp_path / "perf.json"
    pt.export_json(str(path))
    data = json.loads(path.read_text())
    assert "win_rate" in data


def test_export_json_failure(monkeypatch, tmp_path, caplog):
    pt = PerformanceTracker()
    caplog.set_level("ERROR")
    monkeypatch.setattr(
        "builtins.open", lambda *_a, **_k: (_ for _ in ()).throw(Exception("disk full"))
    )
    pt.export_json(str(tmp_path / "fail.json"))
    assert "Failed to export" in caplog.text


def test_alpha_beta_zero_variance_benchmark():
    """Benchmark with zero variance -> beta=0.0 and alpha ~= mean(trades)."""
    from statistics import mean

    import pytest

    pt = PerformanceTracker()
    pt.trades = [1.0, 2.0, 3.0]
    pt.benchmark = [1.0, 1.0, 1.0]  # var_b == 0 => beta == 0.0 path
    res = pt.alpha_beta()
    assert res["beta"] == 0.0
    # With risk_free default 0.0, alpha ~= mean(trades)
    assert res["alpha"] == pytest.approx(mean(pt.trades), rel=1e-6)
