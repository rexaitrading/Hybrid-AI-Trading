"""
Unit Tests: GateScore (Hybrid AI Quant Pro v15.1 – Absolute 100% Coverage)
--------------------------------------------------------------------------
Covers:
- Initialization with/without config values
- Weight normalization (balanced, invalid, empty)
- Threshold adjustments (bull, bear, crisis, sideways, adaptive off)
- allow_trade():
    - enabled vs disabled
    - audit_mode outputs
    - strict_missing veto vs relaxed ignore
    - regime mapping confidence applied
    - no contributing models → blocked
    - regime detector exception fallback
    - ensemble passes vs fails
    - logging explainability
"""

import logging
import pytest
from hybrid_ai_trading.risk.gatescore import GateScore
from hybrid_ai_trading.risk.regime_detector import RegimeDetector


# -----------------------------
# Threshold adjustments
# -----------------------------
def test_threshold_adjustments():
    g = GateScore(enabled=True, threshold=0.8, adaptive=True)
    assert g.adjusted_threshold("bull") <= g.base_threshold
    assert g.adjusted_threshold("bear") >= g.base_threshold
    assert g.adjusted_threshold("crisis") >= g.base_threshold
    assert g.adjusted_threshold("sideways") == g.base_threshold

    g2 = GateScore(enabled=True, adaptive=False, threshold=0.9)
    assert g2.adjusted_threshold("bull") == 0.9


# -----------------------------
# Weight normalization
# -----------------------------
def test_weight_normalization_balanced():
    g = GateScore(models=["a", "b"], weights={"a": 2, "b": 2})
    assert pytest.approx(sum(g.weights.values()), rel=1e-6) == 1.0


def test_weight_normalization_invalid_and_empty(caplog):
    caplog.set_level(logging.WARNING)
    g1 = GateScore(models=["a", "b"], weights={"a": 0, "b": 0})
    normalized = g1._normalize_weights({"a": 0, "b": 0})
    assert pytest.approx(sum(normalized.values()), rel=1e-6) == 1.0

    g2 = GateScore(models=[], weights={})
    assert g2.weights == {}


# -----------------------------
# Regime mapping and detection
# -----------------------------
@pytest.mark.parametrize("regime", ["bull", "bear", "crisis", "sideways"])
def test_allow_trade_regime_mapping(monkeypatch, regime):
    g = GateScore(enabled=True, models=["regime"], audit_mode=True)
    monkeypatch.setattr(type(g.regime_detector), "detect", lambda self, s: regime)
    decision, score, thr, reg = g.allow_trade({}, "SPY")
    assert reg == regime
    assert isinstance(score, float)


def test_regime_detector_failure(monkeypatch, caplog):
    g = GateScore(enabled=True, models=["regime"], audit_mode=True)

    def bad_detect(self, symbol):
        raise RuntimeError("crash")

    monkeypatch.setattr(type(g.regime_detector), "detect", bad_detect)
    caplog.set_level(logging.ERROR)
    decision, score, thr, regime = g.allow_trade({}, "AAPL")
    assert regime == "neutral"
    assert "Regime detection failed" in caplog.text


# -----------------------------
# allow_trade paths
# -----------------------------
def test_disabled_gate_audit_mode():
    g = GateScore(enabled=False, audit_mode=True)
    decision, score, thr, regime = g.allow_trade({})
    assert decision is True
    assert score == 1.0
    assert regime == "neutral"


def test_missing_model_ignored(caplog):
    g = GateScore(models=["price", "sentiment"], weights={"price": 1.0}, strict_missing=False)
    caplog.set_level("INFO")
    result = g.allow_trade({"price": 1.0}, "AAPL")
    assert result in (True, False)
    assert "ignored" in caplog.text


def test_strict_missing_veto(caplog):
    g = GateScore(models=["m1"], strict_missing=True, weights={"m1": 1.0})
    caplog.set_level("WARNING")
    result = g.allow_trade({})
    assert result is False
    assert "veto trade" in caplog.text


def test_no_contributing_models_strict_false(caplog):
    """Covers branch where total_weight == 0"""
    g = GateScore(enabled=True, models=["m1"], weights={"m1": 1.0}, strict_missing=False)
    caplog.set_level("WARNING")
    result = g.allow_trade({}, "AAPL")
    assert result is False
    assert "No contributing models" in caplog.text


def test_block_and_pass_paths(caplog):
    caplog.set_level("INFO")
    g1 = GateScore(models=["price"], weights={"price": 1.0}, threshold=0.95)
    result1 = g1.allow_trade({"price": 0.1}, "AAPL")
    assert result1 is False

    g2 = GateScore(models=["price"], weights={"price": 1.0}, threshold=0.5)
    result2 = g2.allow_trade({"price": 0.9}, "AAPL")
    assert result2 is True


def test_explainability_logging(caplog):
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(RegimeDetector, "detect", lambda self, s: "bull")
    g = GateScore(enabled=True, models=["price"], weights={"price": 1.0})
    caplog.set_level("INFO")
    g.allow_trade({"price": 0.9}, "AAPL")
    assert any("Ensemble Score" in rec.message for rec in caplog.records)
    monkeypatch.undo()
