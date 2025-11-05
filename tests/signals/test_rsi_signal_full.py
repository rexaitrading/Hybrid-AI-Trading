"""
Unit Tests: RSI Signal (Hybrid AI Quant Pro v24.3 Ã¢â‚¬â€œ Hedge-Fund Grade, 100% Coverage)
-----------------------------------------------------------------------------------
Covers ALL branches of rsi_signal:
- Empty bars
- Not enough bars
- Missing 'c' field Ã¢â€ â€™ closes.empty
- NaN close values
- BUY (<30)
- SELL (>70)
- HOLD (inside 30Ã¢â‚¬â€œ70)
- Loss=0 fallback: positive gain Ã¢â€ â€™ SELL
- Loss=0 fallback: non-positive gain Ã¢â€ â€™ BUY
- NaN RSI guard
- Exception handling (parse + rolling)
- Wrapper consistency
"""

import os
import sys

import numpy as np
import pandas as pd

from hybrid_ai_trading.signals.rsi_signal import RSISignal, rsi_signal

# --- Ensure src/ is on sys.path ---
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "src"))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def make_bars(prices):
    """Helper: wrap closes into bar dicts with 'c' key."""
    return [{"c": p} for p in prices]


# ----------------------------------------------------------------------
# Guard Branches
# ----------------------------------------------------------------------
def test_empty_bars():
    assert rsi_signal([]) == "HOLD"


def test_not_enough_bars():
    bars = make_bars(range(10))
    assert rsi_signal(bars, period=14) == "HOLD"


def test_closes_empty_guard():
    bars = [{"x": i} for i in range(20)]
    assert rsi_signal(bars, period=14) == "HOLD"


def test_nan_close_values():
    bars = [{"c": float("nan")}] * 20
    assert rsi_signal(bars) == "HOLD"


# ----------------------------------------------------------------------
# Core Decisions
# ----------------------------------------------------------------------
def test_buy_branch():
    prices = list(range(200, 10, -10))  # steep downward
    assert rsi_signal(make_bars(prices), period=14) == "BUY"


def test_sell_branch():
    prices = list(range(1, 200))  # strong upward momentum
    assert rsi_signal(make_bars(prices), period=14) == "SELL"


def test_hold_branch():
    prices = [
        50,
        52,
        48,
        51,
        49,
        50,
        51,
        49,
        50,
        52,
        48,
        51,
        49,
        50,
        51,
        49,
        50,
        52,
        48,
        51,
    ]
    assert rsi_signal(make_bars(prices), period=14) == "HOLD"


# ----------------------------------------------------------------------
# Fallback Branches
# ----------------------------------------------------------------------
def test_loss_zero_positive_gain():
    prices = list(range(100, 130))  # monotonic gains
    assert rsi_signal(make_bars(prices), period=14) == "SELL"


def test_loss_zero_non_positive_gain():
    prices = [100] * 30  # flat
    assert rsi_signal(make_bars(prices), period=14) == "BUY"


# ----------------------------------------------------------------------
# NaN RSI Branch
# ----------------------------------------------------------------------
def test_nan_rsi_branch(monkeypatch):
    bars = make_bars(range(40))

    class DummyRolling:
        def mean(self, *_a, **_k):
            return pd.Series([np.nan])

    monkeypatch.setattr(pd.Series, "rolling", lambda *_a, **_k: DummyRolling())
    out = RSISignal(period=14).generate("SYM", bars)
    assert out["signal"] == "HOLD"
    assert out["reason"] == "nan rsi"


# ----------------------------------------------------------------------
# Exception Handling
# ----------------------------------------------------------------------
def test_exception_branch_parse(monkeypatch):
    def boom_series(*_a, **_k):
        raise Exception("boom")

    monkeypatch.setattr(pd, "Series", boom_series)
    bars = make_bars(range(20))
    out = RSISignal().generate("SYM", bars)
    assert out["signal"] == "HOLD"
    assert "failed parse" in out["reason"]


def test_exception_branch_calc(monkeypatch):
    """Patch rolling to throw Ã¢â€ â€™ triggers 'calc failed' branch."""

    def boom_rolling(self, *_a, **_k):
        raise Exception("boom")

    monkeypatch.setattr(pd.Series, "rolling", boom_rolling)
    bars = make_bars(range(20))
    out = RSISignal().generate("SYM", bars)
    assert out["signal"] == "HOLD"
    assert "calc failed" in out["reason"]


# ----------------------------------------------------------------------
# Wrapper Coverage
# ----------------------------------------------------------------------
def test_rsi_signal_wrapper_consistency():
    bars = make_bars(list(range(50, 80)) + [20])
    f_result = rsi_signal(bars)
    c_result = RSISignal().generate("AAPL", bars)
    assert f_result == c_result["signal"]
    assert f_result in ("BUY", "SELL", "HOLD")
