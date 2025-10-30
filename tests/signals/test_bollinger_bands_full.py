"""
Unit Tests: BollingerBandsSignal (Hybrid AI Quant Pro v24.0 – Hedge-Fund Grade, 100% Coverage)
----------------------------------------------------------------------------------------------
Covers:
- Insufficient bars
- Missing 'c' close field
- NaN values in closes
- Parse error guard
- Flat stdev branch
- BUY below lower band
- SELL above upper band
- HOLD inside bands
- Wrapper coverage (audit + non-audit)
"""

import math
import statistics

from hybrid_ai_trading.signals.bollinger_bands import (
    BollingerBandsSignal,
    bollinger_bands_signal,
)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def make_bars(values):
    """Wrap close values into bar dicts."""
    return [{"c": v} for v in values]


# ----------------------------------------------------------------------
# Guard branches
# ----------------------------------------------------------------------
def test_insufficient_bars():
    sig = BollingerBandsSignal(period=20)
    result = sig.generate("AAPL", make_bars([100] * 5))
    assert result["signal"] == "HOLD"
    assert result["reason"] == "insufficient_data"


def test_missing_close_field():
    bars = [{"h": 100, "l": 95}] * 25  # no 'c'
    sig = BollingerBandsSignal(period=20)
    result = sig.generate("AAPL", bars)
    assert result["signal"] == "HOLD"
    assert result["reason"] == "missing_close"


def test_nan_values():
    bars = make_bars([100] * 19 + [math.nan])
    sig = BollingerBandsSignal(period=20)
    result = sig.generate("AAPL", bars)
    assert result["signal"] == "HOLD"
    assert result["reason"] == "nan_detected"


def test_parse_error(monkeypatch):
    def bad_mean(_):
        raise ValueError("boom")

    monkeypatch.setattr(statistics, "mean", bad_mean)
    sig = BollingerBandsSignal(period=20)
    bars = make_bars([100] * 25)
    result = sig.generate("AAPL", bars)
    assert result["signal"] == "HOLD"
    assert result["reason"] == "parse_error"


# ----------------------------------------------------------------------
# Decision branches
# ----------------------------------------------------------------------
def test_flat_stdev():
    """All closes equal → stdev=0 → HOLD flat_stdev."""
    bars = make_bars([100] * 25)
    sig = BollingerBandsSignal(period=20)
    result = sig.generate("AAPL", bars)
    assert result["signal"] == "HOLD"
    assert result["reason"] == "flat_stdev"


def test_buy_below_lower_band():
    """Last close well below lower band → BUY."""
    bars = make_bars([100] * 19 + [50])
    sig = BollingerBandsSignal(period=20, std_dev=2.0)
    result = sig.generate("AAPL", bars)
    assert result["signal"] == "BUY"
    assert result["reason"] == "below_lower_band"


def test_sell_above_upper_band():
    """Last close well above upper band → SELL."""
    bars = make_bars([100] * 19 + [200])
    sig = BollingerBandsSignal(period=20, std_dev=2.0)
    result = sig.generate("AAPL", bars)
    assert result["signal"] == "SELL"
    assert result["reason"] == "above_upper_band"


def test_hold_inside_bands():
    """Last close inside bands → HOLD."""
    # Oscillating around SMA
    bars = make_bars([100 + (i % 2) for i in range(25)])
    sig = BollingerBandsSignal(period=20, std_dev=2.0)
    result = sig.generate("AAPL", bars)
    assert result["signal"] == "HOLD"
    assert result["reason"] == "within_bands"


# ----------------------------------------------------------------------
# Wrapper coverage
# ----------------------------------------------------------------------
def test_wrapper_non_audit_and_audit():
    bars = make_bars([100] * 19 + [50])  # BUY case

    # Non-audit mode
    out = bollinger_bands_signal(bars, period=20, std_dev=2.0, audit=False)
    assert out in {"BUY", "SELL", "HOLD"}

    # Audit mode
    decision, close, upper, lower = bollinger_bands_signal(
        bars, period=20, std_dev=2.0, audit=True
    )
    assert decision in {"BUY", "SELL", "HOLD"}
    assert isinstance(close, float)
    assert isinstance(upper, float)
    assert isinstance(lower, float)
