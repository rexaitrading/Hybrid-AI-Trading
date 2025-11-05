"""
Unit Tests: BreakoutV1Signal (Hybrid AI Quant Pro v24.2 Ã¢â‚¬â€œ Hedge-Fund Grade, 100% Coverage)
-----------------------------------------------------------------------------------------
Covers:
- Decision branches: BUY / SELL / HOLD / tie_case
- Guard branches: insufficient bars, NaN detection, parse error
- Wrapper breakout_signal success + exception
- Wrapper fetch failure (wrapper_exception)
- Audit mode with tuple unpacking
- Direct log_decision coverage
"""

from unittest.mock import patch

import pytest

from hybrid_ai_trading.signals.breakout_v1 import BreakoutV1Signal, breakout_signal


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def make_bars(closes, highs=None, lows=None):
    """Helper: build bar dicts with c/h/l values."""
    highs = highs or closes
    lows = lows or closes
    return [{"c": c, "h": h, "l": l} for c, h, l in zip(closes, highs, lows)]


@pytest.fixture
def signal():
    """Fixture: default BreakoutV1Signal with window=3."""
    return BreakoutV1Signal(window=3)


# ----------------------------------------------------------------------
# Decision branches
# ----------------------------------------------------------------------
def test_generate_buy(signal):
    bars = make_bars([1, 2, 10], highs=[2, 3, 5], lows=[0, 1, 2])
    decision, close, prev_high, prev_low = signal.generate("AAPL", bars, audit=True)
    assert decision == "BUY"
    assert close == 10
    assert prev_high == 3
    assert prev_low == 0


def test_generate_sell(signal):
    bars = make_bars([10, 9, 1], highs=[11, 10, 9], lows=[9, 8, 2])
    decision, close, prev_high, prev_low = signal.generate("AAPL", bars, audit=True)
    assert decision == "SELL"
    assert close == 1
    assert prev_high == 11
    assert prev_low == 8


def test_generate_hold(signal):
    bars = make_bars([10, 11, 10], highs=[12, 13, 15], lows=[8, 7, 9])
    decision, close, prev_high, prev_low = signal.generate("AAPL", bars, audit=True)
    assert decision == "HOLD"
    assert prev_high == 13
    assert prev_low == 7


def test_generate_tie_case(signal):
    bars = make_bars([5, 5, 5], highs=[5, 5, 5], lows=[5, 5, 5])
    decision, close, prev_high, prev_low = signal.generate("AAPL", bars, audit=True)
    assert decision == "SELL"
    assert close == 5
    assert prev_high == 5
    assert prev_low == 5


# ----------------------------------------------------------------------
# Guard branches
# ----------------------------------------------------------------------
def test_generate_insufficient(signal):
    out = signal.generate("AAPL", make_bars([100]))
    assert out == "HOLD"


def test_generate_nan_detected(signal):
    bars = make_bars([10, float("nan"), 12])
    decision, close, prev_high, prev_low = signal.generate("AAPL", bars, audit=True)
    assert decision == "HOLD"
    assert isinstance(close, float)
    assert isinstance(prev_high, float)
    assert isinstance(prev_low, float)


def test_generate_parse_error(monkeypatch, signal):
    def bad_float(_):
        raise ValueError("boom")

    monkeypatch.setattr("builtins.float", bad_float)
    bars = make_bars([1, 2, 3])
    out = signal.generate("AAPL", bars)
    assert out == "HOLD"


# ----------------------------------------------------------------------
# Wrapper & Exception coverage
# ----------------------------------------------------------------------
@patch("hybrid_ai_trading.signals.breakout_v1.get_ohlcv_latest")
def test_breakout_signal_success(mock_get):
    mock_get.return_value = make_bars([1, 2, 10], highs=[2, 3, 5], lows=[0, 1, 2])
    out = breakout_signal("AAPL", window=3)
    assert out == "BUY"


@patch("hybrid_ai_trading.signals.breakout_v1.get_ohlcv_latest")
def test_breakout_signal_exception(mock_get):
    mock_get.side_effect = Exception("data error")
    out = breakout_signal("AAPL", window=3)
    assert out == "HOLD"


@patch("hybrid_ai_trading.signals.breakout_v1.get_ohlcv_latest")
def test_generate_wrapper_exception(monkeypatch):
    """Force get_ohlcv_latest to raise Ã¢â€ â€™ wrapper_exception path."""

    def boom(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr("hybrid_ai_trading.signals.breakout_v1.get_ohlcv_latest", boom)
    sig = BreakoutV1Signal(window=3)
    out = sig.generate("AAPL")
    assert out == "HOLD"


# ----------------------------------------------------------------------
# Audit mode
# ----------------------------------------------------------------------
def test_generate_audit_mode(signal):
    bars = make_bars([1, 2, 10], highs=[2, 3, 5], lows=[0, 1, 2])
    decision, close, high, low = signal.generate("AAPL", bars, audit=True)
    assert decision in {"BUY", "SELL", "HOLD"}
    assert isinstance(close, float)
    assert isinstance(high, float)
    assert isinstance(low, float)


# ----------------------------------------------------------------------
# Direct log_decision coverage
# ----------------------------------------------------------------------
def test_log_decision_direct(signal, caplog):
    """Directly call _log_decision to ensure log line is covered."""
    caplog.set_level("INFO")
    signal._log_decision("AAPL", "BUY", "unit_test")
    assert "unit_test" in caplog.text


def test_breakout_v1_window_edge():
    from hybrid_ai_trading.signals.breakout_v1 import breakout_v1

    bars = [{"c": 1, "h": 1, "l": 1} for _ in range(3)]
    assert breakout_v1(bars, window=3) in {"BUY", "SELL", "HOLD"}
