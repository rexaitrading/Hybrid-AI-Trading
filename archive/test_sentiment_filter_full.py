"""
Unit Tests: SentimentFilter (Hybrid AI Quant Pro v14.9 – AAA Hedge-Fund Grade, 100% Coverage)
---------------------------------------------------------------------------------------------
Covers ALL branches of sentiment_filter.py:
- Init: disabled filter, unknown model, fallback paths
- VADER: success, exception, missing polarity_scores, bad return, bad compound
- FinBERT: success, exception, not callable, malformed outputs, bad output type
- Else: invalid model with analyzer=None or dummy analyzer
- Smoothing: normal averaging + history pop
- score(): analyzer None, invalid model else path, forced exception
- allow_trade(): analyzer=None, HOLD allowed, neutral zone allowed, threshold block,
  bias overrides, unknown side, final True (BUY/SELL)
"""

import pytest

import hybrid_ai_trading.risk.sentiment_filter as sf_mod
from hybrid_ai_trading.risk.sentiment_filter import SentimentFilter


# ----------------------------------------------------------------------
# Init and Guards
# ----------------------------------------------------------------------
def test_init_disabled_and_unknown_model():
    sf = SentimentFilter(enabled=False)
    assert sf.analyzer is None
    assert sf.score("text") == 0.5
    assert sf.allow_trade("headline", "BUY")

    with pytest.raises(ValueError):
        SentimentFilter(enabled=True, model="bad")


def test_init_fallback_models_missing(monkeypatch, caplog):
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
        def polarity_scores(self, text):
            return {"compound": 0.5}

    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: FakeAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader")
    score = sf.score("ok")
    assert 0 <= score <= 1


def test_vader_exception(monkeypatch, caplog):
    class Exploder:
        def polarity_scores(self, text):
            raise Exception("boom")

    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: Exploder())
    sf = SentimentFilter(enabled=True, model="vader")
    caplog.set_level("ERROR")
    assert sf.score("fail") == 0.0
    assert "failed" in caplog.text.lower() or "error" in caplog.text.lower()


def test_vader_missing_polarity_scores():
    sf = SentimentFilter(enabled=True, model="vader")
    sf.analyzer = object()  # no polarity_scores
    assert sf.score("ignored") == 0.5


def test_vader_bad_return(monkeypatch, caplog):
    class BadAnalyzer:
        def polarity_scores(self, text):
            return "not-a-dict"

    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: BadAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader")
    caplog.set_level("ERROR")
    assert sf.score("oops") == 0.0


def test_vader_bad_compound(monkeypatch, caplog):
    class BadAnalyzer:
        def polarity_scores(self, text):
            return {"compound": "NaN"}

    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: BadAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader")
    caplog.set_level("ERROR")
    assert sf.score("oops") == 0.0


# ----------------------------------------------------------------------
# FinBERT Paths
# ----------------------------------------------------------------------
def test_finbert_success(monkeypatch):
    def fake_pipeline(task, model=None):
        def analyzer(text):
            return [{"label": "negative", "score": 0.8}]

        return analyzer

    monkeypatch.setattr(sf_mod, "pipeline", fake_pipeline)
    sf = SentimentFilter(enabled=True, model="finbert")
    score = sf.score("ok")
    assert 0 <= score <= 1


def test_finbert_exception(monkeypatch, caplog):
    def fake_pipeline(task, model=None):
        def analyzer(text):
            raise Exception("fail")

        return analyzer

    monkeypatch.setattr(sf_mod, "pipeline", fake_pipeline)
    sf = SentimentFilter(enabled=True, model="finbert")
    caplog.set_level("ERROR")
    assert sf.score("bad") == 0.0


def test_finbert_not_callable():
    sf = SentimentFilter(enabled=True, model="finbert")
    sf.analyzer = object()  # not callable
    assert sf.score("ignored") == 0.5


def test_finbert_malformed(monkeypatch, caplog):
    def fake_pipeline(task, model=None):
        def analyzer(text):
            return [{}]

        return analyzer

    monkeypatch.setattr(sf_mod, "pipeline", fake_pipeline)
    sf = SentimentFilter(enabled=True, model="finbert")
    caplog.set_level("ERROR")
    assert sf.score("oops") == 0.0


def test_finbert_bad_output(monkeypatch, caplog):
    def fake_pipeline(task, model=None):
        def analyzer(text):
            return "not-a-list"

        return analyzer

    monkeypatch.setattr(sf_mod, "pipeline", fake_pipeline)
    sf = SentimentFilter(enabled=True, model="finbert")
    caplog.set_level("ERROR")
    assert sf.score("oops") == 0.0


# ----------------------------------------------------------------------
# Extra score coverage: analyzer None, invalid model, forced exception
# ----------------------------------------------------------------------
def test_score_analyzer_none_branch(caplog):
    sf = SentimentFilter(enabled=True, model="vader")
    sf.analyzer = None
    caplog.set_level("DEBUG")
    assert sf.score("ignored") == 0.5
    assert "analyzer" in caplog.text.lower()


def test_score_unknown_model_else_branch():
    class DummyAnalyzer:
        pass

    sf = SentimentFilter(enabled=True, model="vader")
    sf.model = "strange"
    sf.analyzer = DummyAnalyzer()
    assert sf.score("ignored") == 0.5


def test_score_forced_exception(monkeypatch, caplog):
    class Exploder:
        def polarity_scores(self, text):
            raise Exception("boom")

    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: Exploder())
    sf = SentimentFilter(enabled=True, model="vader")
    caplog.set_level("ERROR")
    assert sf.score("oops") == 0.0


# ----------------------------------------------------------------------
# Smoothing
# ----------------------------------------------------------------------
def test_smoothing_average(monkeypatch):
    class FakeAnalyzer:
        def polarity_scores(self, text):
            return {"compound": 1.0}

    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: FakeAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader", smoothing=3)
    sf.score("a")
    sf.score("b")
    avg = sf.score("c")
    assert 0 <= avg <= 1
    assert len(sf.history) == 3


def test_smoothing_pop(monkeypatch):
    class FakeAnalyzer:
        def polarity_scores(self, text):
            return {"compound": 1.0}

    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: FakeAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader", smoothing=2)
    sf.score("a")
    sf.score("b")
    sf.score("c")
    assert len(sf.history) == 2


# ----------------------------------------------------------------------
# allow_trade
# ----------------------------------------------------------------------
def test_allow_trade_fallback_analyzer_none(caplog):
    sf = SentimentFilter(enabled=True, model="vader")
    sf.analyzer = None
    caplog.set_level("DEBUG")
    assert sf.allow_trade("headline", "BUY")
    assert "allow all" in caplog.text.lower()


def test_allow_trade_hold_side():
    sf = SentimentFilter(enabled=True, model="vader")
    sf.score = lambda *_: 0.0
    assert sf.allow_trade("headline", "HOLD")


def test_allow_trade_neutral_zone(monkeypatch, caplog):
    class FakeAnalyzer:
        def polarity_scores(self, text):
            return {"compound": 0.0}

    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: FakeAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader", threshold=0.0, neutral_zone=1.0)
    caplog.set_level("DEBUG")
    assert sf.allow_trade("headline", "BUY")
    assert "neutral zone" in caplog.text.lower()


def test_allow_trade_threshold_block(monkeypatch, caplog):
    class FakeAnalyzer:
        def polarity_scores(self, text):
            return {"compound": 0.0}

    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: FakeAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader", threshold=1.0, neutral_zone=0.0)
    caplog.set_level("WARNING")
    assert not sf.allow_trade("headline", "BUY")
    assert "blocked" in caplog.text.lower()


def test_allow_trade_bias_overrides(monkeypatch):
    class FakeAnalyzer:
        def polarity_scores(self, text):
            return {"compound": 1.0}

    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: FakeAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader")
    sf.score = lambda *_: 1.0
    sf.bias = "bullish"
    assert not sf.allow_trade("headline", "SELL")
    sf.bias = "bearish"
    assert not sf.allow_trade("headline", "BUY")


def test_allow_trade_unknown_side(monkeypatch, caplog):
    class FakeAnalyzer:
        def polarity_scores(self, text):
            return {"compound": 0.9}

    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: FakeAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader")
    caplog.set_level("DEBUG")
    assert sf.allow_trade("headline", "XXX")
    assert "unknown side" in caplog.text.lower()


def test_allow_trade_final_true_buy_and_sell(monkeypatch):
    class FakeAnalyzer:
        def polarity_scores(self, text):
            return {"compound": 1.0}

    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: FakeAnalyzer())
    sf = SentimentFilter(
        enabled=True, model="vader", threshold=0.5, neutral_zone=0.1, bias="none"
    )
    assert sf.allow_trade("headline", "BUY")
    assert sf.allow_trade("headline", "SELL")


# ----------------------------------------------------------------------
# Extra Coverage Tests for SentimentFilter
# ----------------------------------------------------------------------


def test_finbert_pipeline_none(monkeypatch):
    """Covers case where FinBERT pipeline import is None (analyzer=None)."""
    monkeypatch.setattr(sf_mod, "pipeline", None)
    sf = SentimentFilter(enabled=True, model="finbert")
    assert sf.analyzer is None
    assert sf.score("ignored") == 0.5


def test_finbert_empty_list(monkeypatch, caplog):
    """Covers FinBERT path where analyzer returns empty list → 0.0."""

    def fake_pipeline(task, model=None):
        return lambda text: []

    monkeypatch.setattr(sf_mod, "pipeline", fake_pipeline)
    sf = SentimentFilter(enabled=True, model="finbert")
    caplog.set_level("ERROR")
    assert sf.score("oops") == 0.0
    assert "not list" in caplog.text.lower() or "output" in caplog.text.lower()


def test_score_unknown_model_with_analyzer():
    """
    Covers else branch after init by patching model to unknown value
    while analyzer is not None → should safely return 0.5.
    """

    class DummyAnalyzer:
        def __call__(self, text):
            return 123

    sf = SentimentFilter(enabled=True, model="vader")  # valid init
    sf.model = "something"  # patch to unknown model after init
    sf.analyzer = DummyAnalyzer()
    result = sf.score("ignored")
    assert result == 0.5


def test_score_outer_exception(monkeypatch, caplog):
    """Forces exception after compound calc to cover outer exception block."""

    class BadAnalyzer:
        def polarity_scores(self, text):
            return {"compound": object()}  # not floatable

    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: BadAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader")
    caplog.set_level("ERROR")
    assert sf.score("bad") == 0.0
    assert "failed" in caplog.text.lower() or "error" in caplog.text.lower()


def test_allow_trade_final_true():
    """Covers final allow_trade return True (score passes all checks)."""

    class FakeAnalyzer:
        def polarity_scores(self, text):
            return {"compound": 1.0}

    sf = SentimentFilter(
        enabled=True, model="vader", threshold=0.5, neutral_zone=0.1, bias="none"
    )
    sf.analyzer = FakeAnalyzer()
    # BUY passes threshold, not in neutral zone, no bias → final True path
    assert sf.allow_trade("great earnings", "BUY")


def test_init_raises_value_error(monkeypatch):
    """Force __init__ to raise ValueError when model invalid and analyzers missing."""
    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", None)
    monkeypatch.setattr(sf_mod, "pipeline", None)
    with pytest.raises(ValueError):
        SentimentFilter(enabled=True, model="nonsense")


def test_score_else_return_point():
    """Covers score() final else branch when model patched to unknown with analyzer present."""

    class DummyAnalyzer:
        def __call__(self, text):
            return 123

    sf = SentimentFilter(enabled=True, model="vader")
    sf.model = "strange"
    sf.analyzer = DummyAnalyzer()
    result = sf.score("ignored")
    assert result == 0.5


def test_allow_trade_final_true_return():
    """Covers allow_trade() final return True after all checks pass."""

    class FakeAnalyzer:
        def polarity_scores(self, text):
            return {"compound": 0.9}

    sf = SentimentFilter(
        enabled=True, model="vader", threshold=0.1, neutral_zone=0.0, bias="none"
    )
    sf.analyzer = FakeAnalyzer()
    assert sf.allow_trade("headline positive", "BUY")


def test_init_with_finbert_and_no_pipeline(monkeypatch):
    """Covers __init__ branch lines 58-60 when model=finbert but pipeline missing."""
    monkeypatch.setattr(sf_mod, "pipeline", None)
    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", None)
    sf = SentimentFilter(enabled=True, model="finbert")
    # Analyzer should be None due to missing pipeline
    assert sf.analyzer is None
    assert sf.score("ignored") == 0.5


def test_score_finbert_missing_fields(monkeypatch, caplog):
    """Covers score branch where FinBERT output dict lacks label/score (line 118)."""

    def fake_pipeline(task, model=None):
        return lambda text: [{"foo": "bar"}]  # missing 'label' and 'score'

    monkeypatch.setattr(sf_mod, "pipeline", fake_pipeline)
    sf = SentimentFilter(enabled=True, model="finbert")
    caplog.set_level("ERROR")
    result = sf.score("oops")
    assert result == 0.0
    assert "malformed" in caplog.text.lower()


def test_allow_trade_unknown_side_final_return(monkeypatch):
    """Covers allow_trade() unconditional True at line 151 with unknown side."""

    class FakeAnalyzer:
        def polarity_scores(self, text):
            return {"compound": 0.9}

    sf = SentimentFilter(
        enabled=True, model="vader", threshold=0.1, neutral_zone=0.0, bias="none"
    )
    sf.analyzer = FakeAnalyzer()
    # 'XYZ' side is unknown, should return True (last return)
    assert sf.allow_trade("positive headline", "XYZ")


def test_init_finbert_pipeline_importerror(monkeypatch, caplog):
    """Covers __init__ elif branch (lines 58-60) where pipeline import fails."""

    def fake_pipeline(task, model=None):
        raise ImportError("no model")

    monkeypatch.setattr(sf_mod, "pipeline", fake_pipeline)
    sf = SentimentFilter(enabled=True, model="finbert")
    caplog.set_level("WARNING")
    assert sf.analyzer is None
    assert "fallback" in caplog.text.lower()


def test_score_finbert_neutral_label(monkeypatch):
    """Covers FinBERT path where label is neutral → normalized=0.5 (line 122)."""

    def fake_pipeline(task, model=None):
        return lambda text: [{"label": "neutral", "score": 0.9}]

    monkeypatch.setattr(sf_mod, "pipeline", fake_pipeline)
    sf = SentimentFilter(enabled=True, model="finbert")
    result = sf.score("headline")
    assert result == 0.5


def test_allow_trade_final_true_branch(monkeypatch):
    """Covers allow_trade() last unconditional return True (line 151)."""

    class FakeAnalyzer:
        def polarity_scores(self, text):
            return {"compound": 0.9}

    sf = SentimentFilter(
        enabled=True, model="vader", threshold=0.5, neutral_zone=0.1, bias="none"
    )
    sf.analyzer = FakeAnalyzer()
    # BUY passes threshold, not neutral, no bias → should hit final return True
    assert sf.allow_trade("headline positive", "BUY")
