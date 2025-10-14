import types
import pytest

import hybrid_ai_trading.risk.sentiment_filter as sf_mod
from hybrid_ai_trading.risk.sentiment_filter import SentimentFilter


def test_init_fallback_models_missing(monkeypatch, caplog):
    # Force both analyzers unavailable, assert 'fallback' warning path on vader
    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", None)
    monkeypatch.setattr(sf_mod, "pipeline", None)
    caplog.set_level("WARNING")
    sf = SentimentFilter(enabled=True, model="vader")
    assert sf.analyzer is None
    assert "fallback" in caplog.text.lower()


def test_init_disabled_and_unknown_model():
    # Disabled: legacy contract
    sf = SentimentFilter(enabled=False)
    assert sf.analyzer is None
    assert sf.score("text") == 0.5
    assert sf.allow_trade("headline", "BUY")

    # Enabled + unknown model -> hard error during __init__
    with pytest.raises(ValueError):
        SentimentFilter(enabled=True, model="bad")


def test_neutral_zone_gate_vader(monkeypatch):
    class FakeVader:
        def __init__(self, values):
            self.values = values
        def polarity_scores(self, text):
            return {"compound": self.values[0]}

    sf = SentimentFilter(enabled=True, model="vader", neutral_zone=0.05)
    # below gate -> 0.0
    sf.analyzer = FakeVader([0.04]); assert sf.score("x") == 0.0
    sf.analyzer = FakeVader([-0.03]); assert sf.score("x") == 0.0
    # above gate -> raw
    sf.analyzer = FakeVader([0.12]); assert sf.score("x") == 0.12


def test_neutral_zone_gate_hf(monkeypatch):
    class FakeHF:
        def __init__(self, label, score):
            self._label = label; self._score = score
        def __call__(self, text):
            return [{"label": self._label, "score": self._score}]

    sf = SentimentFilter(enabled=True, model="hf", neutral_zone=0.10)
    sf.analyzer = FakeHF("POSITIVE", 0.08); assert sf.score("x") == 0.0
    sf.analyzer = FakeHF("NEGATIVE", 0.09); assert sf.score("x") == 0.0
    sf.analyzer = FakeHF("POSITIVE", 0.25); assert sf.score("x") == 0.25
    sf.analyzer = FakeHF("NEGATIVE", 0.30); assert sf.score("x") == -0.30


def test_allow_trade_thresholds(monkeypatch):
    class FakeVader:
        def __init__(self, v): self.v=v
        def polarity_scores(self, _): return {"compound": self.v}

    sf = SentimentFilter(enabled=True, model="vader", neutral_zone=0.10, threshold=0.15)
    # gate = max(0.10, 0.15) = 0.15
    sf.analyzer = FakeVader(0.14)
    assert sf.allow_trade("x", "BUY") is False
    sf.analyzer = FakeVader(0.16)
    assert sf.allow_trade("x", "BUY") is True
    sf.analyzer = FakeVader(-0.14)
    assert sf.allow_trade("x", "SELL") is False
    sf.analyzer = FakeVader(-0.20)
    assert sf.allow_trade("x", "SELL") is True