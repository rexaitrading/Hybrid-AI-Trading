"""
Unit Tests: SentimentFilter (Hybrid AI Quant Pro v14.6 – Final AAA Polished)
----------------------------------------------------------------------------
Covers ALL branches of sentiment_filter.py:
- Init: disabled filter, unknown model, fallback paths
- VADER: success, exception, missing polarity_scores, bad return, bad compound
- FinBERT: success, exception, not callable, malformed outputs, bad output type
- Else: invalid model with analyzer=None or dummy analyzer
- Smoothing: normal averaging + history pop
- allow_trade: analyzer=None, HOLD allowed, neutral zone allowed, threshold block,
  bias overrides, unknown side, final True (BUY/SELL)
"""

import pytest
import hybrid_ai_trading.risk.sentiment_filter as sf_mod
from hybrid_ai_trading.risk.sentiment_filter import SentimentFilter


# ----------------------------------------------------------------------
# Init and Guards
# ----------------------------------------------------------------------
def test_init_disabled_and_unknown():
    sf = SentimentFilter(enabled=False)
    assert sf.analyzer is None
    assert sf.score("x") == 0.5
    assert sf.allow_trade("headline", "BUY")

    with pytest.raises(ValueError):
        SentimentFilter(enabled=True, model="bad")


def test_init_fallback_no_models(monkeypatch, caplog):
    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", None)
    monkeypatch.setattr(sf_mod, "pipeline", None)
    caplog.set_level("WARNING")
    sf = SentimentFilter(enabled=True, model="vader")
    assert sf.analyzer is None
    assert "fallback" in caplog.text.lower()


# ----------------------------------------------------------------------
# VADER Paths
# ----------------------------------------------------------------------
def test_vader_success(monkeypatch):
    class FakeAnalyzer:
        def polarity_scores(self, text): return {"compound": 0.5}
    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: FakeAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader")
    assert 0 <= sf.score("ok") <= 1


def test_vader_exception(monkeypatch, caplog):
    class FakeAnalyzer:
        def polarity_scores(self, text): raise Exception("boom")
    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: FakeAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader")
    caplog.set_level("ERROR")
    assert sf.score("fail") == 0.0


def test_vader_missing_polarity_scores():
    sf = SentimentFilter(enabled=True, model="vader")
    sf.analyzer = object()
    assert sf.score("ignored") == 0.5


def test_vader_bad_return(monkeypatch, caplog):
    class BadAnalyzer:
        def polarity_scores(self, text): return "not-a-dict"
    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: BadAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader")
    caplog.set_level("ERROR")
    assert sf.score("oops") == 0.0


def test_vader_bad_compound(monkeypatch, caplog):
    class BadAnalyzer:
        def polarity_scores(self, text): return {"compound": "NaN"}
    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: BadAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader")
    caplog.set_level("ERROR")
    assert sf.score("oops") == 0.0


# ----------------------------------------------------------------------
# FinBERT Paths
# ----------------------------------------------------------------------
def test_finbert_success(monkeypatch):
    def fake_pipeline(task, model=None):
        def fake_analyzer(text): return [{"label": "negative", "score": 0.8}]
        return fake_analyzer
    monkeypatch.setattr(sf_mod, "pipeline", fake_pipeline)
    sf = SentimentFilter(enabled=True, model="finbert")
    assert 0 <= sf.score("ok") <= 1


def test_finbert_exception(monkeypatch, caplog):
    def fake_pipeline(task, model=None):
        def bad_analyzer(text): raise Exception("fail")
        return bad_analyzer
    monkeypatch.setattr(sf_mod, "pipeline", fake_pipeline)
    sf = SentimentFilter(enabled=True, model="finbert")
    caplog.set_level("ERROR")
    assert sf.score("bad") == 0.0


def test_finbert_not_callable():
    sf = SentimentFilter(enabled=True, model="finbert")
    sf.analyzer = object()
    assert sf.score("ignored") == 0.5


def test_finbert_malformed(monkeypatch, caplog):
    def fake_pipeline(task, model=None):
        def bad_analyzer(text): return [{}]
        return bad_analyzer
    monkeypatch.setattr(sf_mod, "pipeline", fake_pipeline)
    sf = SentimentFilter(enabled=True, model="finbert")
    caplog.set_level("ERROR")
    assert sf.score("oops") == 0.0


def test_finbert_bad_output(monkeypatch, caplog):
    def fake_pipeline(task, model=None):
        def bad_analyzer(text): return "not-a-list"
        return bad_analyzer
    monkeypatch.setattr(sf_mod, "pipeline", fake_pipeline)
    sf = SentimentFilter(enabled=True, model="finbert")
    caplog.set_level("ERROR")
    assert sf.score("oops") == 0.0


# ----------------------------------------------------------------------
# Else Branches (Unknown Model Handling)
# ----------------------------------------------------------------------
def test_score_invalid_model_with_none_analyzer():
    sf = SentimentFilter(enabled=True, model="vader")
    sf.model = "weird"
    sf.analyzer = None
    assert sf.score("ignored") == 0.5


def test_score_invalid_model_with_dummy_analyzer():
    class DummyAnalyzer: pass
    sf = SentimentFilter(enabled=True, model="vader")
    sf.model = "unknown"
    sf.analyzer = DummyAnalyzer()
    assert sf.score("ignored") == 0.5


# ----------------------------------------------------------------------
# Smoothing
# ----------------------------------------------------------------------
def test_smoothing(monkeypatch):
    class FakeAnalyzer:
        def polarity_scores(self, text): return {"compound": 1.0}
    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: FakeAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader", smoothing=3)
    sf.score("a"); sf.score("b"); avg = sf.score("c")
    assert 0 <= avg <= 1


def test_smoothing_pop(monkeypatch):
    class FakeAnalyzer:
        def polarity_scores(self, text): return {"compound": 1.0}
    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: FakeAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader", smoothing=2)
    sf.score("a"); sf.score("b"); sf.score("c")
    assert len(sf.history) == 2


# ----------------------------------------------------------------------
# allow_trade Paths
# ----------------------------------------------------------------------
def test_allow_trade_fallback_analyzer_none():
    sf = SentimentFilter(enabled=True, model="vader")
    sf.analyzer = None
    assert sf.allow_trade("headline", "BUY")


def test_allow_trade_hold_side():
    sf = SentimentFilter(enabled=True, model="vader")
    sf.score = lambda *_ , **__: 0.0
    assert sf.allow_trade("headline", "HOLD")


def test_allow_trade_neutral_zone(monkeypatch, caplog):
    class FakeAnalyzer:
        def polarity_scores(self, text): return {"compound": 0.0}
    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: FakeAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader", threshold=0.0, neutral_zone=1.0)
    caplog.set_level("DEBUG")
    assert sf.allow_trade("headline", "BUY")
    assert "neutral zone" in caplog.text.lower()


def test_allow_trade_threshold_block(monkeypatch, caplog):
    class FakeAnalyzer:
        def polarity_scores(self, text): return {"compound": 0.0}
    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: FakeAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader", threshold=1.0, neutral_zone=0.0)
    caplog.set_level("WARNING")
    assert not sf.allow_trade("headline", "BUY")
    assert "blocked" in caplog.text.lower()


def test_allow_trade_bias_overrides(monkeypatch):
    class FakeAnalyzer:
        def polarity_scores(self, text): return {"compound": 1.0}
    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: FakeAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader")
    sf.score = lambda *_ , **__: 1.0

    sf.bias = "bullish"
    assert not sf.allow_trade("headline", "SELL")

    sf.bias = "bearish"
    assert not sf.allow_trade("headline", "BUY")


def test_allow_trade_unknown_side(monkeypatch, caplog):
    class FakeAnalyzer:
        def polarity_scores(self, text): return {"compound": 0.9}
    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: FakeAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader")
    caplog.set_level("DEBUG")
    assert sf.allow_trade("headline", "XXX")
    assert "unknown side" in caplog.text.lower()


def test_allow_trade_final_true_buy_and_sell(monkeypatch):
    class FakeAnalyzer:
        def polarity_scores(self, text): return {"compound": 1.0}
    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: FakeAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader",
                         threshold=0.5, neutral_zone=0.1, bias="none")
    assert sf.allow_trade("headline", "BUY")
    assert sf.allow_trade("headline", "SELL")
