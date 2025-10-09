"""
Unit Tests: SentimentFilter (Hybrid AI Quant Pro – AAA Hedge-Fund Grade)
Covers ALL branches of sentiment_filter.py:
- Init: disabled filter, unknown model, fallback paths (vader/finbert missing)
- VADER: success, exception, missing polarity_scores, bad return, bad compound
- FinBERT: success, exception, not callable, malformed outputs, bad output type
- Score: analyzer None, unknown model after init, forced outer exception, smoothing average/pop
- allow_trade: analyzer=None, HOLD allowed, neutral zone allowed, threshold block,
  bias overrides, unknown side, final True (BUY/SELL)
- Module import warnings: force ImportError for vaderSentiment/transformers and reload module
"""

import importlib
import sys

import pytest

import hybrid_ai_trading.risk.sentiment_filter as sf_mod
from hybrid_ai_trading.risk.sentiment_filter import SentimentFilter


# ----------------------------------------------------------------------
# Init guards
# ----------------------------------------------------------------------
def test_init_disabled_and_unknown_model():
    sf = SentimentFilter(enabled=False)
    assert sf.analyzer is None
    assert sf.score("text") == 0.5
    assert sf.allow_trade("headline", "BUY")

    with pytest.raises(ValueError):
        SentimentFilter(enabled=True, model="bad")


def test_init_fallback_models_missing(monkeypatch, caplog):
    # Force both analyzers unavailable, assert fallback warning path
    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", None)
    monkeypatch.setattr(sf_mod, "pipeline", None)
    caplog.set_level("WARNING")
    sf = SentimentFilter(enabled=True, model="vader")
    assert sf.analyzer is None
    assert "fallback" in caplog.text.lower()


# ----------------------------------------------------------------------
# VADER paths
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
# FinBERT paths
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
            return [{}]  # missing fields

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
# Extra score() coverage: analyzer None, unknown model, forced exception
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
    sf.model = "strange"  # patch to unknown AFTER init
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
# Module import warnings coverage (top-level try/except imports)
# ----------------------------------------------------------------------
def test_module_import_warnings_reload(monkeypatch, caplog):
    """
    Force ImportError for vaderSentiment and transformers, reload module to exercise
    the top-level warning paths that may be skipped when packages are installed.
    """
    import builtins

    caplog.set_level("WARNING")

    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name.startswith("vaderSentiment") or name == "transformers":
            raise ImportError("missing for test")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    sys.modules.pop("hybrid_ai_trading.risk.sentiment_filter", None)
    mod2 = importlib.import_module("hybrid_ai_trading.risk.sentiment_filter")
    assert "not installed" in caplog.text.lower()


# ---------------------------
# Extra micro-tests to close remaining uncovered lines
# ---------------------------


def test_init_finbert_pipeline_raises_general_exception(monkeypatch, caplog):
    """Covers __init__ try/except for finbert when pipeline() raises at construction (lines ~58–60)."""
    import hybrid_ai_trading.risk.sentiment_filter as sf_mod

    caplog.set_level("WARNING")

    def bad_pipeline(task, model=None):
        raise RuntimeError("init fail")

    monkeypatch.setattr(sf_mod, "pipeline", bad_pipeline)
    sf = SentimentFilter(enabled=True, model="finbert")
    # Fallback path: analyzer becomes None and warning logged
    assert sf.analyzer is None
    assert "fallback" in caplog.text.lower() or "unavailable" in caplog.text.lower()


def test_vader_compound_numeric_nan(monkeypatch, caplog):
    """Covers VADER numeric NaN branch (lines ~96–98)."""
    import hybrid_ai_trading.risk.sentiment_filter as sf_mod

    class NanAnalyzer:
        def polarity_scores(self, text):
            return {"compound": float("nan")}

    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: NanAnalyzer())
    sf = SentimentFilter(enabled=True, model="vader")
    caplog.set_level("ERROR")
    assert sf.score("any") == 0.0
    assert "nan" in caplog.text.lower()


def test_finbert_positive_and_neutral_labels(monkeypatch):
    """Covers FinBERT positive (normalized = score) and neutral (=0.5) (lines ~122)."""
    import hybrid_ai_trading.risk.sentiment_filter as sf_mod

    def pipe_pos(task, model=None):
        return lambda text: [{"label": "POSITIVE", "score": 0.73}]

    monkeypatch.setattr(sf_mod, "pipeline", pipe_pos)
    sf_pos = SentimentFilter(enabled=True, model="finbert")
    assert sf_pos.score("x") == pytest.approx(0.73, rel=1e-6)

    def pipe_neu(task, model=None):
        return lambda text: [{"label": "neutral", "score": 0.99}]

    monkeypatch.setattr(sf_mod, "pipeline", pipe_neu)
    sf_neu = SentimentFilter(enabled=True, model="finbert")
    assert sf_neu.score("y") == 0.5


def test_finbert_malformed_dict_missing_fields_again(monkeypatch, caplog):
    """Reassert malformed dict path (line ~118) with different shape to ensure exact line executes."""
    import hybrid_ai_trading.risk.sentiment_filter as sf_mod

    def bad_pipe(task, model=None):
        return lambda text: [{"label_only": "pos"}]  # missing 'score'

    monkeypatch.setattr(sf_mod, "pipeline", bad_pipe)
    caplog.set_level("ERROR")
    sf = SentimentFilter(enabled=True, model="finbert")
    assert sf.score("z") == 0.0
    assert "malformed" in caplog.text.lower() or "score" in caplog.text.lower()


def test_allow_trade_unknown_side_precise_debug(monkeypatch, caplog):
    """Directly exercise the 'unknown side → allowed' return (line ~151) with analyzer present."""
    import hybrid_ai_trading.risk.sentiment_filter as sf_mod

    class FakeAnalyzer:
        def polarity_scores(self, text):
            return {"compound": 0.9}

    monkeypatch.setattr(sf_mod, "SentimentIntensityAnalyzer", lambda: FakeAnalyzer())
    sf = SentimentFilter(
        enabled=True, model="vader", threshold=0.5, neutral_zone=0.0, bias="none"
    )
    caplog.set_level("DEBUG")
    assert sf.allow_trade("headline", "XYZ") is True
    assert "unknown side" in caplog.text.lower()


def test_vader_compound_numeric_nan(monkeypatch, caplog):
    """Covers VADER numeric NaN branch even if the module was reloaded earlier."""

    class NanAnalyzer:
        def polarity_scores(self, text):
            return {"compound": float("nan")}

    # Build filter (may fallback analyzer=None depending on prior reloads)
    sf = SentimentFilter(enabled=True, model="vader")
    # Force the analyzer so the VADER branch executes deterministically
    sf.analyzer = NanAnalyzer()

    caplog.set_level("ERROR")
    assert sf.score("any") == 0.0
    assert "nan" in caplog.text.lower()


def test_finbert_positive_and_neutral_labels(monkeypatch):
    """
    Stable FinBERT pos/neutral coverage that does not rely on module-level pipeline being set.
    We set the analyzer directly so the branch executes even after earlier module reload tests.
    """
    # POSITIVE -> normalized = score
    sf_pos = SentimentFilter(enabled=True, model="finbert")
    sf_pos.analyzer = lambda text: [{"label": "POSITIVE", "score": 0.73}]
    assert sf_pos.score("x") == pytest.approx(0.73, rel=1e-6)

    # NEUTRAL -> normalized = 0.5
    sf_neu = SentimentFilter(enabled=True, model="finbert")
    sf_neu.analyzer = lambda text: [{"label": "neutral", "score": 0.99}]
    assert sf_neu.score("y") == 0.5


def test_finbert_malformed_dict_missing_fields_again(monkeypatch, caplog):
    """
    Force FinBERT malformed dict branch even if pipeline was disabled earlier:
    set analyzer directly to return a list with dict missing required keys.
    """
    caplog.set_level("ERROR")
    sf = SentimentFilter(enabled=True, model="finbert")
    # Set analyzer directly to return a malformed list of dicts (no label/score).
    sf.analyzer = lambda text: [{"label_only": "pos"}]
    out = sf.score("z")
    assert out == 0.0
    assert "malformed" in caplog.text.lower() or "score" in caplog.text.lower()


def test_allow_trade_unknown_side_precise_debug(monkeypatch, caplog):
    """
    Force the 'unknown side -> allowed' branch even if earlier tests set analyzer=None:
    set analyzer directly on the instance so allow_trade does not return early.
    """

    class FakeAnalyzer:
        def polarity_scores(self, text):
            return {"compound": 0.9}

    sf = SentimentFilter(
        enabled=True, model="vader", threshold=0.5, neutral_zone=0.0, bias="none"
    )
    # Ensure analyzer IS set (avoid early 'Analyzer=None -> allow all trades' branch)
    sf.analyzer = FakeAnalyzer()

    caplog.set_level("DEBUG")
    assert sf.allow_trade("headline", "XYZ") is True
    # exact debug log from the unknown-side branch
    assert "unknown side" in caplog.text.lower()


def test_finbert_init_pipeline_raises_fallback(monkeypatch, caplog):
    """
    Hit __init__ try/except for finbert when pipeline raises at construction (lines ~58–60).
    Ensures we execute the fallback warning in the initializer itself.
    """
    import hybrid_ai_trading.risk.sentiment_filter as sf_mod

    caplog.set_level("WARNING")

    def raising_pipeline(task, model=None):
        raise RuntimeError("init-failure")

    monkeypatch.setattr(sf_mod, "pipeline", raising_pipeline)
    sf = SentimentFilter(enabled=True, model="finbert")
    # Fallback: analyzer None and warning logged
    assert sf.analyzer is None
    assert "fallback" in caplog.text.lower() or "unavailable" in caplog.text.lower()


def test_vader_compound_numeric_nan_instance_analyzer(caplog):
    """
    Force the VADER numeric NaN branch (lines ~96–98) regardless of module import state
    by setting the analyzer on the instance directly.
    """

    class NanAnalyzer:
        def polarity_scores(self, text):
            return {"compound": float("nan")}

    sf = SentimentFilter(enabled=True, model="vader")
    sf.analyzer = NanAnalyzer()  # ensure we do NOT return early on analyzer=None
    caplog.set_level("ERROR")
    assert sf.score("any") == 0.0
    assert "nan" in caplog.text.lower()


def test_allow_trade_unknown_side_with_instance_analyzer(caplog):
    """
    Hit the 'unknown side -> allowed' log line (line ~151) by ensuring analyzer is present
    so allow_trade does not return early.
    """

    class FakeAnalyzer:
        def polarity_scores(self, text):
            return {"compound": 0.9}

    sf = SentimentFilter(
        enabled=True, model="vader", threshold=0.5, neutral_zone=0.0, bias="none"
    )
    sf.analyzer = FakeAnalyzer()  # ensure analyzer present
    caplog.set_level("DEBUG")
    assert sf.allow_trade("headline", "XYZ") is True
    assert "unknown side" in caplog.text.lower()


def test_finbert_init_constructor_raises_fallback(monkeypatch, caplog):
    """Hit __init__ finbert try/except (lines 58–60) by raising during pipeline construction."""
    import hybrid_ai_trading.risk.sentiment_filter as sf_mod

    caplog.set_level("WARNING")

    def raising_pipeline(task, model=None):
        raise RuntimeError("ctor-fail")

    monkeypatch.setattr(sf_mod, "pipeline", raising_pipeline)
    sf = SentimentFilter(enabled=True, model="finbert")
    assert sf.analyzer is None
    assert "fallback" in caplog.text.lower() or "unavailable" in caplog.text.lower()


def test_vader_compound_nan_with_instance_analyzer(caplog):
    """Force VADER numeric NaN branch (96–98) regardless of import state by setting analyzer on instance."""

    class NanAnalyzer:
        def polarity_scores(self, text):
            return {"compound": float("nan")}

    sf = SentimentFilter(enabled=True, model="vader")
    sf.analyzer = NanAnalyzer()  # ensure we're in the VADER branch
    caplog.set_level("ERROR")
    assert sf.score("txt") == 0.0
    assert "nan" in caplog.text.lower()


def test_allow_trade_unknown_side_line_151(caplog):
    """Ensure the exact unknown-side debug line executes by using an instance analyzer."""

    class FakeAnalyzer:
        def polarity_scores(self, text):
            return {"compound": 0.9}

    sf = SentimentFilter(
        enabled=True, model="vader", threshold=0.5, neutral_zone=0.0, bias="none"
    )
    sf.analyzer = FakeAnalyzer()
    caplog.set_level("DEBUG")
    assert sf.allow_trade("headline", "XYZ") is True
    assert "unknown side" in caplog.text.lower()


def test_finbert_ctor_raise_precise(monkeypatch, caplog):
    import hybrid_ai_trading.risk.sentiment_filter as sf_mod

    caplog.set_level("WARNING")

    def ctor_raise(task, model=None):
        raise RuntimeError("ctor-fail-exact")

    monkeypatch.setattr(sf_mod, "pipeline", ctor_raise)
    sf = SentimentFilter(enabled=True, model="finbert")
    assert sf.analyzer is None
    assert "fallback" in caplog.text.lower() or "unavailable" in caplog.text.lower()


def test_vader_nan_precise(caplog):
    class NanAnalyzer:
        def polarity_scores(self, text):
            return {"compound": float("nan")}

    sf = SentimentFilter(enabled=True, model="vader")
    sf.analyzer = NanAnalyzer()
    caplog.set_level("ERROR")
    assert sf.score("t") == 0.0
    assert "nan" in caplog.text.lower()


def test_unknown_side_precise(caplog):
    class A:
        def polarity_scores(self, text):
            return {"compound": 0.9}

    sf = SentimentFilter(
        enabled=True, model="vader", threshold=0.5, neutral_zone=0.0, bias="none"
    )
    sf.analyzer = A()
    caplog.set_level("DEBUG")
    assert sf.allow_trade("h", "XYZ") is True
    assert "unknown side" in caplog.text.lower()
# ---- neutral zone gate tests ----
def test_neutral_zone_gate_vader(monkeypatch):
    import hybrid_ai_trading.risk.sentiment_filter as sf_mod

    class FakeVader:
        def __init__(self, values):
            self.values = values
        def polarity_scores(self, text):
            return {"compound": self.values[0]}

    # small positive below gate -> 0.0
    sf = sf_mod.SentimentFilter(enabled=True, model="vader", neutral_zone=0.05)
    sf.analyzer = FakeVader([0.04])
    assert sf.score("x") == 0.0

    # small negative below gate -> 0.0
    sf.analyzer = FakeVader([-0.03])
    assert sf.score("x") == 0.0

    # above gate -> raw score preserved
    sf.analyzer = FakeVader([0.12])
    assert sf.score("x") == 0.12

def test_neutral_zone_gate_hf(monkeypatch):
    import hybrid_ai_trading.risk.sentiment_filter as sf_mod

    class FakeHF:
        def __init__(self, label, score):
            self._label = label
            self._score = score
        def __call__(self, text):
            return [{"label": self._label, "score": self._score}]

    sf = sf_mod.SentimentFilter(enabled=True, model="hf", neutral_zone=0.10)
    sf.analyzer = FakeHF("POSITIVE", 0.08)
    assert sf.score("x") == 0.0  # below gate

    sf.analyzer = FakeHF("NEGATIVE", 0.09)
    assert sf.score("x") == 0.0  # below gate (magnitude)

    sf.analyzer = FakeHF("POSITIVE", 0.25)
    assert sf.score("x") == 0.25  # above gate

    sf.analyzer = FakeHF("NEGATIVE", 0.30)
    assert sf.score("x") == -0.30  # above gate, negative preserved
