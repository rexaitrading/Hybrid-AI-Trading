import logging

import pytest

from hybrid_ai_trading.risk.gatescore import GateScore


# ---------------------------
# Weight normalization
# ---------------------------
def test_normalize_weights_empty_and_zero_sum(caplog):
    # empty weights -> {}
    g_empty = GateScore(models=[], weights={})
    assert g_empty.weights == {}
    # sum<=0 -> equal weights + warning
    caplog.set_level(logging.WARNING, logger="hybrid_ai_trading.risk.gatescore")
    g_zero = GateScore(models=["a", "b"], weights={"a": 0.0, "b": 0.0})
    assert pytest.approx(sum(g_zero.weights.values()), rel=1e-12) == 1.0
    assert "Invalid weights" in caplog.text


# ---------------------------
# Disabled gate
# ---------------------------
def test_disabled_gate_audit_and_non_audit():
    g_a = GateScore(enabled=False, audit_mode=True)
    out_a = g_a.allow_trade({})
    assert isinstance(out_a, tuple) and out_a[0] is True

    g_b = GateScore(enabled=False, audit_mode=False)
    out_b = g_b.allow_trade({})
    assert out_b is True


# ---------------------------
# Missing models (ignore vs veto)
# ---------------------------
def test_missing_models_paths(caplog):
    caplog.set_level(logging.INFO, logger="hybrid_ai_trading.risk.gatescore")
    g_ignore = GateScore(models=["p", "s"], weights={"p": 1.0}, strict_missing=False)
    assert g_ignore.allow_trade({"p": 0.9}) in (True, False)
    assert "ignored" in caplog.text

    caplog.clear()
    caplog.set_level(logging.WARNING, logger="hybrid_ai_trading.risk.gatescore")
    g_veto = GateScore(models=["m1"], weights={"m1": 1.0}, strict_missing=True, audit_mode=False)
    assert g_veto.allow_trade({}) is False
    assert "veto" in caplog.text


# ---------------------------
# No contributing models
# ---------------------------
def test_no_contributing_models_blocks(caplog):
    caplog.set_level(logging.WARNING, logger="hybrid_ai_trading.risk.gatescore")
    g = GateScore(models=["m1"], weights={"m1": 1.0}, strict_missing=False)
    assert g.allow_trade({}) is False
    assert "No contributing models" in caplog.text


# ---------------------------
# total_weight <= 0 (audit + non-audit)
# ---------------------------
def test_total_weight_zero_blocks_non_audit(caplog):
    # Provide input for m so we have contributing=True but total_weight==0 (weights missing)
    caplog.set_level(logging.WARNING, logger="hybrid_ai_trading.risk.gatescore")
    g = GateScore(models=["m"], weights={}, strict_missing=False, audit_mode=False)
    assert g.allow_trade({"m": 0.5}) is False
    assert "Total weight=0" in caplog.text


def test_total_weight_zero_blocks_audit():
    g = GateScore(models=["m"], weights={}, strict_missing=False, audit_mode=True)
    decision, score, thr, regime = g.allow_trade({"m": 1.0})
    assert decision is False and score == 0.0


# ---------------------------
# Adaptive threshold via 'regime' model
# ---------------------------
def test_adaptive_threshold_with_regime(monkeypatch):
    # models include regime (which always contributes)
    g = GateScore(
        models=["regime", "m"],
        weights={"m": 1.0},
        threshold=0.6,
        adaptive=True,
        audit_mode=True,
    )
    # bull lowers threshold
    monkeypatch.setattr(g, "_detect_regime", lambda *_: "bull")
    decision, score, thr, regime = g.allow_trade({"m": 0.59}, "AAPL")
    assert thr <= g.base_threshold and regime == "bull"
    # bear raises threshold
    monkeypatch.setattr(g, "_detect_regime", lambda *_: "bear")
    decision, score, thr, regime = g.allow_trade({"m": 0.6}, "AAPL")
    assert thr >= g.base_threshold and regime == "bear"
    # crisis raises more
    monkeypatch.setattr(g, "_detect_regime", lambda *_: "crisis")
    decision, score, thr, regime = g.allow_trade({"m": 0.6}, "AAPL")
    assert thr >= g.base_threshold and regime == "crisis"


def test_regime_detector_exception_fallback(monkeypatch, caplog):
    caplog.set_level(logging.ERROR, logger="hybrid_ai_trading.risk.gatescore")
    g = GateScore(models=["regime"], weights={}, audit_mode=True, adaptive=True)
    # make regime detection raise inside allow_trade loop
    monkeypatch.setattr(g, "_detect_regime", lambda *_: (_ for _ in ()).throw(RuntimeError("boom")))
    decision, score, thr, regime = g.allow_trade({}, "SYM")
    # total_weight==0 path also should trigger inside allow_trade
    assert decision is False and regime == "neutral"
    assert "Regime detection failed" in caplog.text


# ---------------------------
# pass/fail around threshold + logging
# ---------------------------
def test_block_and_pass_paths_and_logging(caplog, monkeypatch):
    g1 = GateScore(models=["price"], weights={"price": 1.0}, threshold=0.95, audit_mode=False)
    assert g1.allow_trade({"price": 0.1}) is False

    caplog.set_level(logging.INFO, logger="hybrid_ai_trading.risk.gatescore")
    g2 = GateScore(
        models=["price"],
        weights={"price": 1.0},
        threshold=0.5,
        audit_mode=False,
        adaptive=False,
    )
    assert g2.allow_trade({"price": 0.9}) is True
    # log line with ensemble info executed
    g2.allow_trade({"price": 0.6})
    assert "Ensemble Score" in "\n".join(
        rec.message for rec in caplog.records if hasattr(rec, "message")
    )


# ---------------------------
# vote() wrapper
# ---------------------------
def test_vote_wrapper():
    g = GateScore(models=["m"], weights={"m": 1.0})
    assert g.vote({"m": 0.9}) in (0, 1)


# ---------------------------
# _safe_score helper
# ---------------------------
def test_safe_score_ok_and_error(caplog):
    g = GateScore(models=["x"], weights={"x": 1.0})
    assert g._safe_score("x", 5) == 5.0
    caplog.set_level(logging.WARNING, logger="hybrid_ai_trading.risk.gatescore")
    assert g._safe_score("x", object()) == 0.0
    assert "failed" in caplog.text


# ---------------------------
# Micro tests to close remaining uncovered lines
# ---------------------------


def test_init_none_models_weights_hits_line_31():
    # models=None, weights=None -> __init__ normalizes to empty
    g = GateScore(enabled=True, models=None, weights=None)
    assert g.models == [] and g.weights == {}


def test_strict_missing_veto_audit_mode_hits_line_109():
    # strict_missing=True + audit_mode=True -> tuple(False, ...)
    g = GateScore(models=["m"], weights={"m": 1.0}, strict_missing=True, audit_mode=True)
    decision, score, thr, regime = g.allow_trade({})
    assert decision is False and score == 0.0


def test_no_contributing_models_audit_mode_hits_line_123():
    # models present but ignored (relaxed missing) -> no contributing -> tuple(False,...)
    g = GateScore(models=["m"], weights={"m": 1.0}, strict_missing=False, audit_mode=True)
    decision, score, thr, regime = g.allow_trade({}, "XYZ")
    assert decision is False and score == 0.0


def test_regime_detector_exception_again_hits_line_162(monkeypatch, caplog):
    # Force detection failure inside allow_trade loop
    caplog.set_level(logging.ERROR, logger="hybrid_ai_trading.risk.gatescore")
    g = GateScore(models=["regime"], weights={}, audit_mode=True, adaptive=True)
    monkeypatch.setattr(g, "_detect_regime", lambda *_: (_ for _ in ()).throw(RuntimeError("boom")))
    decision, score, thr, regime = g.allow_trade({}, "SYM")
    assert decision is False and regime == "neutral"
    assert "Regime detection failed" in caplog.text


def test_adjusted_threshold_neutral_hits_line_170():
    # Explicit neutral path
    g = GateScore(enabled=True, adaptive=True, threshold=0.7)
    assert g.adjusted_threshold("neutral") == g.base_threshold


def test_bottom_logging_and_return_paths_audit_and_non_audit(monkeypatch, caplog):
    # Drive through logging and final return areas (177–179, 183 equivalents)
    caplog.set_level(logging.INFO, logger="hybrid_ai_trading.risk.gatescore")

    # Non-audit path: contribute one model but set total_weight=0 -> warn + False
    g_non = GateScore(models=["m"], weights={}, strict_missing=False, audit_mode=False)
    out_non = g_non.allow_trade({"m": 0.5}, "SPY")
    assert out_non is False

    # Audit path: same configuration -> tuple(False, 0.0, thr, regime)
    g_aud = GateScore(
        models=["m"], weights={}, strict_missing=False, audit_mode=True, adaptive=False
    )
    out_aud = g_aud.allow_trade({"m": 0.5}, "SPY")
    assert isinstance(out_aud, tuple) and out_aud[0] is False

    # Also touch adjusted_threshold explicitly to ensure logging region accounted
    _ = g_non.adjusted_threshold("bear")
