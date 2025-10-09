"""
Unit Tests: BlackSwanGuard (Hybrid AI Quant Pro v12.7 – Hedge-Fund Grade, 100% Coverage)
----------------------------------------------------------------------------------------
Covers:
- Initialization
- trigger_event()
- clear_event() (exists / does not exist)
- clear_all() (with / without events)
- active() (True / False)
- filter_signal():
  * No events → passes through
  * Active → blocks BUY/SELL
  * Active → passes HOLD
  * Active → passes unknown signals unchanged
"""

import pytest

from hybrid_ai_trading.risk.black_swan_guard import BlackSwanGuard


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def guard():
    return BlackSwanGuard()


# ----------------------------------------------------------------------
# Initialization
# ----------------------------------------------------------------------
def test_initial_state(guard):
    assert guard.events == {}
    assert guard.active() is False


# ----------------------------------------------------------------------
# Trigger event
# ----------------------------------------------------------------------
def test_trigger_event_and_active(guard):
    guard.trigger_event("system", "crash")
    assert "system" in guard.events
    assert guard.events["system"] == "crash"
    assert guard.active() is True


# ----------------------------------------------------------------------
# Clear event
# ----------------------------------------------------------------------
def test_clear_event_existing(guard):
    guard.trigger_event("system", "halt")
    guard.clear_event("system")
    assert "system" not in guard.events
    assert guard.active() is False


def test_clear_event_non_existing(guard):
    guard.clear_event("ghost")  # should not raise
    assert guard.active() is False


# ----------------------------------------------------------------------
# Clear all
# ----------------------------------------------------------------------
def test_clear_all_with_events(guard):
    guard.trigger_event("system", "halt")
    guard.trigger_event("exchange", "halt")
    guard.clear_all()
    assert guard.events == {}
    assert guard.active() is False


def test_clear_all_without_events(guard):
    guard.clear_all()  # no crash, remains empty
    assert guard.events == {}
    assert guard.active() is False


# ----------------------------------------------------------------------
# Filter signal
# ----------------------------------------------------------------------
def test_filter_signal_no_events(guard):
    assert guard.filter_signal("BUY") == "BUY"
    assert guard.filter_signal("SELL") == "SELL"
    assert guard.filter_signal("HOLD") == "HOLD"
    assert guard.filter_signal("UNKNOWN") == "UNKNOWN"


def test_filter_signal_blocked_when_active(guard):
    guard.trigger_event("system", "halt")
    assert guard.filter_signal("BUY") == "HOLD"
    assert guard.filter_signal("SELL") == "HOLD"


def test_filter_signal_hold_and_unknown_pass(guard):
    guard.trigger_event("system", "halt")
    assert guard.filter_signal("HOLD") == "HOLD"
    assert guard.filter_signal("XYZ") == "XYZ"
