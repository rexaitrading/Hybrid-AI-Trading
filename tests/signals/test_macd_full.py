"""
Unit Tests: MACD Signal (Hybrid AI Quant Pro v16.6 â€“ Hedge-Fund Grade, 100% Coverage)
------------------------------------------------------------------------------------
Covers every branch of macd.py:
- Guards: empty bars, not enough bars, missing/NaN closes, empty closes, NaN MACD/Signal
- Crossovers: BUY crossover, SELL crossover
- Trend confirmations: BUY (above), SELL (below), HOLD
- Exception handling
- Wrapper consistency
"""

import pandas as pd
import pytest

from hybrid_ai_trading.signals.macd import MACDSignal, macd_signal


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def make_bars(prices):
    """Convert a list of closes into bar dicts."""
    return [{"c": p} for p in prices]


def fake_ewm_factory(sequences):
    """Fake .ewm() monkeypatch for deterministic tests."""
    call_count = {"n": 0}

    def fake_ewm(self, span, adjust=False):
        class Dummy:
            def mean(_self):
                call_count["n"] += 1
                return sequences[call_count["n"] - 1]

        return Dummy()

    return fake_ewm


# ----------------------------------------------------------------------
# Guard branches
# ----------------------------------------------------------------------
def test_empty_bars():
    # Wrapper returns just "HOLD"
    assert macd_signal([]) == "HOLD"
    # Class generate returns dict with reason
    out = MACDSignal().generate("SYM", [])
    assert out["signal"] == "HOLD"
    assert "no bars" in out["reason"]


def test_not_enough_bars():
    result = macd_signal(make_bars(range(10)))
    assert result == "HOLD"
    out = MACDSignal().generate("SYM", make_bars(range(10)))
    assert "not enough bars" in out["reason"]


def test_missing_close_field():
    out = MACDSignal().generate("SYM", [{"o": 1, "h": 2}] * 50)
    assert out["signal"] == "HOLD"
    assert "invalid" in out["reason"]


def test_empty_closes():
    out = MACDSignal().generate("SYM", [{"x": 1}, {"y": 2}])
    assert out["signal"] == "HOLD"
    assert "invalid" in out["reason"]


def test_nan_in_closes():
    out = MACDSignal().generate("SYM", [{"c": 100.0}] * 49 + [{"c": float("nan")}])
    assert out["signal"] == "HOLD"
    assert "nan detected" in out["reason"]


# ----------------------------------------------------------------------
# Crossovers
# ----------------------------------------------------------------------
def test_buy_crossover(monkeypatch):
    ema_fast = pd.Series([1.0, 4.0])  # macd = [-1, 3]
    ema_slow = pd.Series([2.0, 1.0])
    signal_line = pd.Series([2.0, 1.0])  # -1<2 and 3>1 â†’ BUY
    monkeypatch.setattr(
        pd.Series, "ewm", fake_ewm_factory([ema_fast, ema_slow, signal_line])
    )
    out = MACDSignal().generate("AAPL", make_bars(range(50)))
    assert out["signal"] == "BUY"


def test_sell_crossover(monkeypatch):
    ema_fast = pd.Series([5.0, 1.0])  # macd = [3, -1]
    ema_slow = pd.Series([2.0, 2.0])
    signal_line = pd.Series([1.0, 2.0])  # 3>1 and -1<2 â†’ SELL
    monkeypatch.setattr(
        pd.Series, "ewm", fake_ewm_factory([ema_fast, ema_slow, signal_line])
    )
    out = MACDSignal().generate("AAPL", make_bars(range(50)))
    assert out["signal"] == "SELL"


# ----------------------------------------------------------------------
# Trend confirmations
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "prices,expected",
    [
        (list(range(1, 100)), "BUY"),  # uptrend
        (list(range(100, 0, -1)), "SELL"),  # downtrend
    ],
)
def test_macd_trend_confirmations(prices, expected):
    assert macd_signal(make_bars(prices)) == expected


def test_macd_hold_explicit(monkeypatch):
    """Force macd == signal_line â†’ HOLD final else branch."""
    ema_fast = pd.Series([1.0, 2.0])
    ema_slow = pd.Series([0.5, 1.5])
    signal_line = pd.Series([0.5, 0.5])  # final macd == signal
    monkeypatch.setattr(
        pd.Series, "ewm", fake_ewm_factory([ema_fast, ema_slow, signal_line])
    )
    out = MACDSignal().generate("AAPL", make_bars(range(50)))
    assert out["signal"] == "HOLD"


# ----------------------------------------------------------------------
# NaN protection inside MACD/Signal
# ----------------------------------------------------------------------
def test_nan_in_macd_or_signal(monkeypatch):
    ema_fast = pd.Series([1.0, 2.0])
    ema_slow = pd.Series([0.5, 1.0])
    signal_line = pd.Series([float("nan"), float("nan")])
    monkeypatch.setattr(
        pd.Series, "ewm", fake_ewm_factory([ema_fast, ema_slow, signal_line])
    )
    out = MACDSignal().generate("AAPL", make_bars(range(50)))
    assert out["signal"] == "HOLD"
    assert "nan macd" in out["reason"]


# ----------------------------------------------------------------------
# Exception handling
# ----------------------------------------------------------------------
def test_exception_branch(monkeypatch):
    def boom_series(*_a, **_k):
        raise Exception("boom")

    monkeypatch.setattr(pd, "Series", boom_series)
    out = MACDSignal().generate("SYM", make_bars(range(50)))
    assert out["signal"] == "HOLD"
    assert "invalid" in out["reason"]


# ----------------------------------------------------------------------
# Wrapper consistency
# ----------------------------------------------------------------------
def test_macd_signal_wrapper_class_consistency():
    bars = make_bars(list(range(1, 100)))
    wrapper = macd_signal(bars)
    klass = MACDSignal().generate("AAPL", bars)["signal"]
    assert wrapper == klass
    assert klass in ("BUY", "SELL", "HOLD")
