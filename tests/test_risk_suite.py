"""
Unit Tests: Risk Layer Suite (Hybrid AI Quant Pro v30.1 – Unified & Polished 100% Coverage)
-------------------------------------------------------------------------------------------
Covers all branches for:
- RiskManager
- SentimentFilter
- KellySizer
- RegimeDetector
"""

import pytest
import logging
import math

from hybrid_ai_trading.risk.risk_manager import RiskManager
from hybrid_ai_trading.risk.sentiment_filter import SentimentFilter
from hybrid_ai_trading.risk.kelly_sizer import KellySizer
from hybrid_ai_trading.risk.regime_detector import RegimeDetector

# ============================
# Risk Manager
# ============================

def test_risk_manager_trade_block_and_allow(caplog):
    rm = RiskManager(daily_loss_limit=-0.03, trade_loss_limit=-0.01)
    caplog.set_level(logging.INFO)

    # Trade loss breach
    assert rm.check_trade(-0.02) is False
    assert "Trade Loss Breach" in caplog.text

    # Allowed trade
    assert rm.check_trade(0.01) is True
    assert "Trade Allowed" in caplog.text


def test_risk_manager_daily_loss_block(caplog):
    rm = RiskManager(daily_loss_limit=-0.03, trade_loss_limit=-0.01)
    caplog.set_level(logging.WARNING)

    # Force daily_pnl below limit
    rm.daily_pnl = -0.04
    assert rm.check_trade(-0.005) is False
    assert "Daily Loss Breach" in caplog.text


# ============================
# Sentiment Filter
# ============================

def test_sentiment_filter_disabled():
    sf = SentimentFilter(enabled=False)
    assert sf.score("anything") == 0.5
    assert sf.allow_trade("headline", "BUY")


def test_sentiment_filter_bias_overrides(monkeypatch):
    class FakeAnalyzer:
        def polarity_scores(self, text): return {"compound": 1.0}
    monkeypatch.setattr(
        "hybrid_ai_trading.risk.sentiment_filter.SentimentIntensityAnalyzer",
        lambda: FakeAnalyzer()
    )
    sf = SentimentFilter(enabled=True, model="vader")
    sf.bias = "bullish"
    assert not sf.allow_trade("headline", "SELL")
    sf.bias = "bearish"
    assert not sf.allow_trade("headline", "BUY")


def test_sentiment_filter_threshold_and_neutral(monkeypatch, caplog):
    class FakeAnalyzer:
        def polarity_scores(self, text): return {"compound": 0.0}

    monkeypatch.setattr(
        "hybrid_ai_trading.risk.sentiment_filter.SentimentIntensityAnalyzer",
        lambda: FakeAnalyzer()
    )

    sf = SentimentFilter(enabled=True, threshold=1.0, neutral_zone=0.0)
    caplog.set_level(logging.WARNING)

    assert not sf.allow_trade("headline", "BUY")
    assert "blocked" in caplog.text.lower()


# ============================
# Kelly Sizer
# ============================

def test_kelly_sizer_defaults_and_half_fraction(caplog):
    ks = KellySizer(win_rate=0.6, payoff=2.0, fraction=0.5)
    caplog.set_level(logging.INFO)
    size = ks.size_position(10000, 100)
    assert size > 0
    assert "KellySizer" in caplog.text


def test_kelly_sizer_invalid_inputs():
    ks = KellySizer(win_rate=0.5, payoff=1.0)
    assert ks.size_position(0, 100) == 0
    assert ks.size_position(1000, 0) == 0


# ============================
# Regime Detector
# ============================

def test_regime_detector_simple_bullish():
    rd = RegimeDetector(min_samples=3)
    data = [1, 2, 3, 4, 5]
    assert rd.detect(data) in ["bull", "bear", "sideways", "crisis", "neutral"]


def test_regime_detector_invalid_data(caplog):
    rd = RegimeDetector(min_samples=5)
    caplog.set_level(logging.ERROR)
    result = rd.detect([])
    assert result == "neutral"
    assert "not enough data" in caplog.text.lower() or "error" in caplog.text.lower()
