"""
Unit Tests: Signal Demo (Hybrid AI Quant Pro v100 – Polished)
-------------------------------------------------------------
Small demo tests for breakout_v1 and breakout_signal.
"""

import logging
from unittest.mock import patch

from hybrid_ai_trading.signals.breakout_v1 import breakout_signal, breakout_v1


def make_bars(prices):
    return [{"c": p} for p in prices]


def test_breakout_v1_basic_decisions():
    bars = make_bars([1, 2, 10])
    assert breakout_v1(bars, window=3) in ["BUY", "SELL", "HOLD"]


def test_breakout_v1_audit_mode():
    bars = make_bars([1, 5, 10])
    decision, price, rh, rl = breakout_v1(bars, window=3, audit=True)
    assert decision in ["BUY", "SELL", "HOLD"]
    assert isinstance(price, float)


def test_breakout_signal_with_valid_bars():
    bars = [{"c": 1}, {"c": 2}, {"c": 3}]
    assert breakout_signal("AAPL", bars=bars) in ["BUY", "SELL", "HOLD"]


def test_breakout_signal_invalid_format(caplog):
    caplog.set_level(logging.ERROR)
    bars = [{"x": 1}]
    result = breakout_signal("AAPL", bars=bars)
    assert result == "HOLD"
    assert "invalid bar format" in caplog.text.lower()


@patch("hybrid_ai_trading.signals.breakout_v1.get_ohlcv_latest")
def test_breakout_signal_fetch_none(mock_get):
    mock_get.return_value = None
    result = breakout_signal("AAPL")
    assert result == "HOLD"
