import pytest
from hybrid_ai_trading.risk.black_swan_guard import BlackSwanGuard

@pytest.fixture
def guard():
    return BlackSwanGuard()

def test_initial_state_and_active_false(guard):
    assert guard.events == {}
    assert guard.active() is False

def test_trigger_event_and_active_true(guard):
    guard.trigger_event("system", "crash")
    assert "system" in guard.events
    assert guard.events["system"] == "crash"
    assert guard.active() is True

def test_clear_event_existing_makes_inactive(guard):
    guard.trigger_event("system", "halt")
    guard.clear_event("system")
    assert "system" not in guard.events
    assert guard.active() is False

def test_clear_event_non_existing_is_noop(guard):
    guard.clear_event("ghost")  # should not raise
    assert guard.active() is False
    assert guard.events == {}

def test_clear_all_with_events(guard):
    guard.trigger_event("system", "halt")
    guard.trigger_event("exchange", "halt")
    guard.clear_all()
    assert guard.events == {}
    assert guard.active() is False

def test_clear_all_without_events_is_noop(guard):
    guard.clear_all()
    assert guard.events == {}
    assert guard.active() is False

def test_filter_signal_no_events_passthrough(guard):
    # With no events, signals pass through unchanged
    assert guard.filter_signal("BUY") == "BUY"
    assert guard.filter_signal("SELL") == "SELL"
    assert guard.filter_signal("HOLD") == "HOLD"
    assert guard.filter_signal("UNKNOWN") == "UNKNOWN"

def test_filter_signal_blocks_buy_sell_when_active(guard):
    guard.trigger_event("system", "halt")
    assert guard.filter_signal("BUY") == "HOLD"
    assert guard.filter_signal("SELL") == "HOLD"

def test_filter_signal_hold_and_unknown_pass_when_active(guard):
    guard.trigger_event("system", "halt")
    assert guard.filter_signal("HOLD") == "HOLD"
    assert guard.filter_signal("XYZ") == "XYZ"
