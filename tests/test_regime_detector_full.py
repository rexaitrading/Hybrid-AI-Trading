"""
Unit Tests: RegimeDetector (Hybrid AI Quant Pro v15.3 – Absolute 100% Coverage)
-------------------------------------------------------------------------------
Covers:
- Initialization
- detect():
    - Disabled mode
    - Not enough data (65–66)
    - Cleaned data too short
    - Crisis regime
    - Bull regime
    - Bear regime (99–100)
    - Sideways regime
    - All-equal prices (fallback)
    - Empty returns branch
    - Exception branch
    - DB branch (patched SessionLocal + Price with proper stubs)
    - DB error branch
- confidence() for all regimes
- reset() clears history (133)
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from hybrid_ai_trading.risk.regime_detector import RegimeDetector


# --- Dummy DB stubs ---
class DummyPrice:
    """Mimics SQLAlchemy Price model with datetime support."""
    symbol = "AAPL"

    class TimestampColumn:
        @staticmethod
        def asc():
            return "timestamp ASC"

        def __ge__(self, other):
            return True

    timestamp = TimestampColumn()

    def __init__(self, close, symbol="AAPL", timestamp=None):
        self.close = close
        self.symbol = symbol
        self.timestamp_value = timestamp or datetime.utcnow()

    def __repr__(self):
        return f"<DummyPrice {self.symbol} close={self.close} at {self.timestamp_value}>"


class DummySession:
    def __init__(self, prices):
        self._prices = prices

    def query(self, model): return self
    def filter(self, *a, **k): return self
    def order_by(self, *a, **k): return self
    def all(self): return self._prices
    def close(self): return None


class BrokenSession:
    def query(self, *a, **k): raise Exception("DB down")
    def close(self): return None


# --- Fixtures ---
@pytest.fixture
def default_detector():
    return RegimeDetector(
        lookback_days=30,
        bull_threshold=0.01,
        bear_threshold=-0.01,
        crisis_volatility=0.05,
        min_samples=3,
        neutral_tolerance=0.001,
    )


# --- Initialization ---
def test_init_defaults():
    d = RegimeDetector()
    assert isinstance(d.lookback_days, int)
    assert d.history == {}


# --- Disabled mode ---
def test_detect_disabled(default_detector):
    default_detector.enabled = False
    assert default_detector.detect("AAPL", prices=[100, 101]) == "neutral"


# --- Not enough / cleaned data ---
def test_detect_not_enough_data(default_detector, caplog):
    caplog.set_level("WARNING")
    default_detector.min_samples = 10
    result = default_detector.detect("AAPL", prices=[100, 101])
    assert result == "sideways"
    assert "Insufficient data" in caplog.text


def test_detect_cleaned_data_too_short(default_detector):
    assert default_detector.detect("AAPL", prices=[np.nan, None, 100]) == "sideways"


# --- Crisis regime ---
def test_detect_crisis(default_detector, caplog):
    caplog.set_level("WARNING")
    prices = [100, 200, 50, 150, 90]
    assert default_detector.detect("AAPL", prices=prices) == "crisis"
    assert "Crisis regime" in caplog.text


# --- Bull regime ---
def test_detect_bull(default_detector):
    prices = [100, 105, 110, 115, 120]
    assert default_detector.detect("AAPL", prices=prices) == "bull"


# --- Bear regime (explicit branch) ---
def test_explicit_bear_branch(default_detector):
    """Force avg_return <= bear_threshold without triggering crisis."""
    default_detector.bear_threshold = -0.01
    default_detector.crisis_volatility = 1.0  # disable crisis
    prices = [100, 98, 96, 94, 92]  # steady decline
    result = default_detector.detect("AAPL", prices=prices)
    assert result == "bear"


# --- Sideways regime ---
def test_detect_sideways(default_detector):
    prices = [100, 101, 99, 100, 101]
    assert default_detector.detect("AAPL", prices=prices) == "sideways"


# --- All-equal prices ---
def test_detect_all_equal_prices(default_detector):
    prices = [100, 100, 100, 100, 100]
    assert default_detector.detect("AAPL", prices=prices) == "sideways"


# --- Empty returns branch ---
def test_detect_empty_returns(default_detector):
    prices = [100, 100, 100]  # pct_change = NaN
    assert default_detector.detect("AAPL", prices=prices) == "sideways"


# --- Exception branch ---
def test_detect_exception_branch(monkeypatch):
    d = RegimeDetector()
    monkeypatch.setattr(
        "numpy.polyfit",
        lambda *a, **k: (_ for _ in ()).throw(Exception("boom"))
    )
    assert d.detect("AAPL", prices=[1, 2, 3, 4, 5]) == "sideways"


# --- DB branch ---
def test_detect_db_branch(monkeypatch):
    now = datetime.utcnow()
    dummy_prices = [
        DummyPrice(100, timestamp=now - timedelta(days=2)),
        DummyPrice(105, timestamp=now - timedelta(days=1)),
        DummyPrice(110, timestamp=now),
    ]
    monkeypatch.setattr(
        "hybrid_ai_trading.risk.regime_detector.SessionLocal",
        lambda: DummySession(dummy_prices),
    )
    monkeypatch.setattr("hybrid_ai_trading.risk.regime_detector.Price", DummyPrice)

    d = RegimeDetector(min_samples=2)
    result = d.detect("AAPL")
    assert result in ("bull", "sideways", "bear", "crisis")


# --- DB error branch ---
def test_detect_db_error(monkeypatch):
    monkeypatch.setattr(
        "hybrid_ai_trading.risk.regime_detector.SessionLocal",
        lambda: BrokenSession(),
    )
    d = RegimeDetector()
    result = d.detect("AAPL")
    assert result == "neutral"


# --- Confidence scoring ---
def test_confidence_all_regimes(monkeypatch):
    d = RegimeDetector()
    monkeypatch.setattr(d, "detect", lambda *a, **k: "bull")
    assert d.confidence("AAPL") == 0.9
    monkeypatch.setattr(d, "detect", lambda *a, **k: "bear")
    assert d.confidence("AAPL") == 0.1
    monkeypatch.setattr(d, "detect", lambda *a, **k: "crisis")
    assert d.confidence("AAPL") == 0.5
    monkeypatch.setattr(d, "detect", lambda *a, **k: "sideways")
    assert d.confidence("AAPL") == 0.5


# --- Reset ---
def test_reset_logs_info(default_detector, caplog):
    """Covers reset() log message (133)."""
    default_detector.history["AAPL"] = ["bull"]
    caplog.set_level("INFO")
    default_detector.reset()
    assert default_detector.history == {}
    assert any("Resetting regime history" in rec.message for rec in caplog.records)

def test_force_bear_branch_without_crisis(default_detector):
    """Force avg_return <= bear_threshold while disabling crisis to cover 99–100."""
    default_detector.bear_threshold = -0.001
    default_detector.crisis_volatility = 1.0  # high so crisis never triggers
    prices = [100, 99, 98, 97, 96]  # steady decline, low volatility
    result = default_detector.detect("AAPL", prices=prices)
    assert result == "bear"


def test_reset_logs_message_branch(default_detector, caplog):
    """Covers reset() log message branch at line 133."""
    default_detector.history["AAPL"] = ["bull"]
    caplog.set_level("INFO")
    default_detector.reset()
    assert default_detector.history == {}
    # Explicitly assert log line so coverage marks it executed
    assert any("Resetting regime history" in rec.message for rec in caplog.records)

def test_force_bear_branch_no_crisis(default_detector):
    """Force avg_return <= bear_threshold while disabling crisis (covers 99–100)."""
    default_detector.bear_threshold = -0.001
    default_detector.crisis_volatility = 1.0  # disable crisis trigger
    prices = [100, 99, 98, 97, 96]  # steady decline, low volatility
    result = default_detector.detect("AAPL", prices=prices)
    assert result == "bear"


def test_reset_log_line_coverage(default_detector, caplog):
    """Covers reset() logging line (133)."""
    default_detector.history["AAPL"] = ["bull"]
    caplog.set_level("INFO")
    default_detector.reset()
    assert default_detector.history == {}
    # Explicit check ensures coverage marks the logger line as executed
    assert any("Resetting regime history" in rec.message for rec in caplog.records)
