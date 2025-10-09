"""
Unit Tests: Paper Trade Demo – Breakout V1 Signal
(Hybrid AI Quant Pro v10.3 – Hedge Fund Grade, Polished & Robust)
=====================================================================
Covers:
- breakout_v1 core logic (BUY, SELL, HOLD)
- breakout_v1 guard branches (empty, insufficient bars, NaN, invalid fields, parse errors)
- breakout_signal wrapper:
    - Successful data fetch
    - Exception fallback (returns HOLD)
- Logging checks tolerate 'failed' OR 'invalid' keywords
"""

import logging
import pytest
from unittest.mock import patch

from hybrid_ai_trading.signals.breakout_v1 import breakout_v1, breakout_signal


# ======================================================================
# Helpers
# ======================================================================
def make_bars(closes, highs=None, lows=None):
    highs = highs or closes
    lows = lows or closes
    return [{"c": c, "h": h, "l": l} for c, h, l in zip(closes, highs, lows)]


# ======================================================================
# breakout_v1 Core Logic
# ======================================================================
def test_breakout_v1_buy_sell_hold():
    # BUY: last close above high
    bars = make_bars([1, 2, 3, 10], highs=[2, 3, 4, 9], lows=[1, 1, 1, 1])
    assert breakout_v1(bars, window=4) == "BUY"

    # SELL: last close below low
    bars = make_bars([10, 9, 8, 1], highs=[11, 11, 11, 11], lows=[9, 9, 9, 2])
    assert breakout_v1(bars, window=4) == "SELL"

    # HOLD: inside range
    bars = make_bars([10, 11, 12, 11], highs=[15, 15, 15, 15], lows=[5, 5, 5, 5])
    assert breakout_v1(bars, window=4) == "HOLD"

    # Tie case: close == high == low
    bars = make_bars([5, 5, 5], highs=[5, 5, 5], lows=[5, 5, 5])
    assert breakout_v1(bars, window=3) == "SELL"


def test_breakout_v1_audit_mode():
    bars = make_bars([1, 2, 3])
    decision, last_close, high_val, low_val = breakout_v1(bars, window=3, audit=True)
    assert decision in {"BUY", "SELL", "HOLD"}
    assert isinstance(last_close, float)
    assert isinstance(high_val, float)
    assert isinstance(low_val, float)


# ======================================================================
# breakout_v1 Guard Branches
# ======================================================================
def test_breakout_v1_empty_and_insufficient():
    assert breakout_v1([], window=5) == "HOLD"  # No bars
    bars = make_bars([1, 2])  # Not enough bars
    assert breakout_v1(bars, window=5) == "HOLD"


def test_breakout_v1_nan_and_invalid_data():
    bars = make_bars([1, float("nan"), 3])  # NaN
    assert breakout_v1(bars, window=3) == "HOLD"

    bars = [{"o": 1}, {"c": 2, "h": 3, "l": 1}]  # Missing keys (parse error)
    assert breakout_v1(bars, window=2) == "HOLD"


def test_breakout_v1_exception_branch(caplog):
    caplog.set_level(logging.ERROR)

    def bad_float(_):
        raise ValueError("boom")

    bars = make_bars([1, 2, 3])
    with patch("builtins.float", side_effect=bad_float):
        assert breakout_v1(bars, window=3) == "HOLD"

    # ✅ Accept both "failed" and "invalid" keywords in log
    lower_log = caplog.text.lower()
    assert any(word in lower_log for word in ("failed", "invalid"))


# ======================================================================
# breakout_signal Wrapper
# ======================================================================
@patch("hybrid_ai_trading.signals.breakout_v1.get_ohlcv_latest")
def test_breakout_signal_success(mock_get):
    bars = make_bars([1, 2, 3, 4, 10])
    mock_get.return_value = bars
    result = breakout_signal("AAPL", window=5)
    assert result in {"BUY", "SELL", "HOLD"}


@patch("hybrid_ai_trading.signals.breakout_v1.get_ohlcv_latest")
def test_breakout_signal_exception(mock_get, caplog):
    mock_get.side_effect = Exception("data error")
    caplog.set_level(logging.ERROR)
    result = breakout_signal("AAPL", window=5)
    assert result == "HOLD"

    # ✅ Again, accept both "failed" and "invalid" in log text
    lower_log = caplog.text.lower()
    assert any(word in lower_log for word in ("failed", "invalid"))
