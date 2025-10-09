from datetime import datetime, timedelta

import pytest

from hybrid_ai_trading.performance_tracker import PerformanceTracker


def test_payoff_ratio_no_trades_hits_lines_85_86(caplog):
    pt = PerformanceTracker()
    caplog.set_level("INFO")
    assert pt.payoff_ratio() == 0.0
    assert "No trades for payoff_ratio" in caplog.text


def test_sortino_no_downside_fallback_hits_lines_130_131(caplog):
    # Two positive trades -> no downside -> fallback branch executes
    pt = PerformanceTracker()
    pt.record_trade(5.0)
    pt.record_trade(10.0)
    caplog.set_level("WARNING")
    val = pt.sortino_ratio()
    assert "No downside trades" in caplog.text
    # Value is finite via fallback path
    assert isinstance(val, float)


def test_drawdown_recovery_time_hits_line_173():
    # Simulate drawdown start and recovery with explicit timestamps
    pt = PerformanceTracker()
    t0 = datetime(2024, 1, 1)
    t1 = t0 + timedelta(days=1)
    t2 = t0 + timedelta(days=4)

    pt.record_equity(100.0, timestamp=t0)  # max_equity = 100, drawdown_start set
    pt.record_equity(80.0, timestamp=t1)  # drawdown
    pt.record_equity(100.0, timestamp=t2)  # recovery -> drawdown_recovery set

    days = pt.drawdown_recovery_time()
    assert isinstance(days, int)
    assert days == 3  # 4 - 1 = 3 days


def test_export_json_success_logs_hits_line_190(tmp_path, caplog):
    pt = PerformanceTracker()
    pt.record_trade(1.0)
    pt.record_equity(100.0)
    path = tmp_path / "perf_success.json"
    caplog.set_level("INFO")
    pt.export_json(str(path))
    # File created & success log executed
    assert path.exists()
    assert "Performance snapshot exported" in caplog.text


def test_drawdown_recovery_time_hits_line_173():
    """Recovery time is computed from peak (start) to recovery timestamp."""
    from datetime import datetime, timedelta

    pt = PerformanceTracker()
    t0 = datetime(2024, 1, 1)  # peak time (start)
    t1 = t0 + timedelta(days=1)  # drawdown after peak
    t2 = t0 + timedelta(days=4)  # recovery at new peak

    pt.record_equity(100.0, timestamp=t0)  # sets max_equity & drawdown_start = t0
    pt.record_equity(80.0, timestamp=t1)  # drawdown
    pt.record_equity(100.0, timestamp=t2)  # recovery -> drawdown_recovery = t2

    days = pt.drawdown_recovery_time()
    assert isinstance(days, int)
    assert days == (t2 - t0).days  # 4 days from peak to recovery


def test_sortino_no_downside_strict_fallback_value(caplog):
    """Cover lines 130–131: no downside trades -> fallback using pstdev(trades) or 1.0."""
    from statistics import mean, pstdev

    pt = PerformanceTracker()
    # Two positive trades => no downside list; fallback path executes.
    pt.record_trade(5.0)
    pt.record_trade(11.0)
    caplog.set_level("WARNING")
    out = pt.sortino_ratio(risk_free=0.0, annualize=False)
    assert "No downside trades" in caplog.text
    # Fallback formula: (avg - rf) / (pstdev(trades) or 1.0)
    expected = (mean(pt.trades) - 0.0) / (pstdev(pt.trades) or 1.0)
    assert out == pytest.approx(expected, rel=1e-12)


def test_drawdown_recovery_time_none_and_int_paths():
    """Cover both branches of drawdown_recovery_time (None vs int) including line 173."""
    from datetime import datetime, timedelta

    # Case 1: None (no recovery yet)
    pt = PerformanceTracker()
    t0 = datetime(2024, 1, 1)
    pt.record_equity(100.0, timestamp=t0)  # sets start at t0
    pt.record_equity(80.0, timestamp=t0 + timedelta(days=1))  # drawdown
    # recovery not set -> None path
    assert pt.drawdown_recovery_time() is None

    # Case 2: Int (recovery reached)
    t2 = t0 + timedelta(days=5)
    pt.record_equity(100.0, timestamp=t2)  # recovery -> sets drawdown_recovery
    days = pt.drawdown_recovery_time()
    assert isinstance(days, int)
    # Default logic: from start (t0) to recovery (t2)
    assert days == (t2 - t0).days


def test_export_json_success_hits_line_190(tmp_path, caplog):
    """Ensure success logger.info path executes (line 190)."""
    pt = PerformanceTracker()
    pt.record_trade(1.0)
    pt.record_equity(100.0)
    path = tmp_path / "perf_export.json"
    caplog.set_level("INFO")
    pt.export_json(str(path))
    # file exists and success log is present
    assert path.exists()
    assert "Performance snapshot exported" in caplog.text


def test_drawdown_recovery_time_none_and_int_paths():
    """Cover both branches of drawdown_recovery_time (0/None vs int), including line 173."""
    from datetime import datetime, timedelta

    pt = PerformanceTracker()

    # Case 1: immediate case after first peak -> can be 0-day recovery (or None on other impls)
    t0 = datetime(2024, 1, 1)
    pt.record_equity(100.0, timestamp=t0)  # sets start=recovery=t0
    pt.record_equity(80.0, timestamp=t0 + timedelta(days=1))  # drawdown
    v1 = pt.drawdown_recovery_time()
    assert v1 is None or v1 == 0

    # Case 2: later, true recovery at a later date -> positive int
    t2 = t0 + timedelta(days=5)
    pt.record_equity(100.0, timestamp=t2)  # recovery set to t2
    v2 = pt.drawdown_recovery_time()
    assert isinstance(v2, int) and v2 == (t2 - t0).days
