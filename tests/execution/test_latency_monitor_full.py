"""
Unit Tests: LatencyMonitor (Hybrid AI Quant Pro v2.6 – Hedge-Fund OE Grade, 100% Coverage)
==========================================================================================
Covers ALL branches in latency_monitor.py:
- reset() clears state
- measure() ok path
- measure() warning path (latency > threshold)
- measure() halting path (breaches >= max_breaches)
- measure() exception branch
- rolling average calculation
- get_stats() snapshot output
"""

import time
import logging
import pytest
from hybrid_ai_trading.execution.latency_monitor import LatencyMonitor


# ----------------------------------------------------------------------
# Test helpers
# ----------------------------------------------------------------------
def fast_func(x):
    return x * 2


def slow_func(x):
    time.sleep(0.01)  # ~10ms delay
    return x + 1


def boom_func(_):
    raise ValueError("bad func")


# ----------------------------------------------------------------------
def test_reset_and_ok_path(caplog):
    lm = LatencyMonitor(threshold_ms=100)
    caplog.set_level(logging.DEBUG)

    res = lm.measure(fast_func, 5)
    assert res["status"] == "ok"
    assert res["result"] == 10
    assert lm.breach_count == 0
    assert not lm.halt

    stats = lm.get_stats()
    assert "avg_latency" in stats
    assert stats["samples"] == 1

    lm.reset()
    assert lm.breach_count == 0
    assert not lm.halt
    assert len(lm.samples) == 0
    assert "reset" in caplog.text


# ----------------------------------------------------------------------
def test_warning_and_halt_paths(caplog):
    lm = LatencyMonitor(threshold_ms=1, max_breaches=2)  # very small threshold
    caplog.set_level(logging.WARNING)

    # First slow call -> warning
    res1 = lm.measure(slow_func, 1)
    assert res1["status"] == "warning"
    assert lm.breach_count == 1
    assert not lm.halt
    assert "Latency breach" in caplog.text

    # Second slow call -> should HALT (not warning anymore)
    res2 = lm.measure(slow_func, 2)
    assert res2["status"] == "halt"
    assert lm.breach_count >= 2
    assert lm.halt
    assert "HALTING trading" in caplog.text


# ----------------------------------------------------------------------
def test_exception_branch(caplog):
    lm = LatencyMonitor(threshold_ms=100)
    caplog.set_level(logging.ERROR)

    res = lm.measure(boom_func, 1)
    assert res["status"] == "error"
    assert isinstance(res["result"], Exception)
    assert "LatencyMonitor caught exception" in caplog.text


# ----------------------------------------------------------------------
def test_avg_latency_and_stats():
    lm = LatencyMonitor(threshold_ms=100)
    assert lm._avg_latency() == 0.0  # no samples yet

    lm.samples.extend([0.1, 0.2, 0.3])
    avg = lm._avg_latency()
    assert 0.19 < avg < 0.21  # ~0.2 average

    stats = lm.get_stats()
    assert stats["samples"] == 3
    assert "avg_latency" in stats
    assert "last_latency" in stats
