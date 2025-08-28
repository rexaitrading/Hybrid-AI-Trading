import pytest
from src.risk.black_swan_guard import BlackSwanGuard


def test_black_swan_blocks_signal():
    guard = BlackSwanGuard()
    guard.trigger_event("news_sentiment_ai", reason="Market crash detected")
    assert guard.active()
    assert guard.filter_signal("BUY") == "HOLD"


def test_black_swan_allows_signal_when_clear():
    guard = BlackSwanGuard()
    assert not guard.active()
    assert guard.filter_signal("BUY") == "BUY"


def test_black_swan_clear_event():
    guard = BlackSwanGuard()
    guard.trigger_event("orderbook_anomaly_ai", reason="Liquidity gap")
    assert guard.active()
    guard.clear_event("orderbook_anomaly_ai")
    assert not guard.active()
