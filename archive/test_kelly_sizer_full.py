"""
Unit Tests: KellySizer (Hybrid AI Quant Pro v13.1 – Hedge Fund OE Grade, 100% Coverage)
---------------------------------------------------------------------------------------
Covers:
- Initialization (defaults + custom)
- kelly_fraction (scaled, clamped, veto, invalid inputs, exception)
- size_position (dict return: valid, invalid inputs, exception, veto)
- batch_size for multi-symbol sizing
- update_params and __repr__
- save_params persistence + failure
- _safe_fmt success and failure branches
"""

import logging
import os
import json
import pytest
from hybrid_ai_trading.risk.kelly_sizer import KellySizer, _safe_fmt


# ----------------------------------------------------------------------
# Init
# ----------------------------------------------------------------------

def test_init_defaults_and_custom(caplog):
    caplog.set_level(logging.INFO)
    ks1 = KellySizer()
    ks2 = KellySizer(0.6, 2.0, 0.5, 0.8)
    assert isinstance(ks1, KellySizer)
    assert isinstance(ks2, KellySizer)
    assert "KellySizer initialized" in caplog.text


# ----------------------------------------------------------------------
# Kelly fraction
# ----------------------------------------------------------------------

def test_kelly_fraction_scaled_and_clamped(caplog):
    caplog.set_level(logging.DEBUG)
    ks = KellySizer(0.6, 2.0, 0.5, 1.0)
    f = ks.kelly_fraction()
    assert 0 <= f <= 1
    assert "Kelly fraction" in caplog.text

    # Risk veto should force 0
    assert ks.kelly_fraction(risk_veto=True) == 0.0

    # Clamp at >1
    ks.fraction = 10.0
    f2 = ks.kelly_fraction()
    assert f2 <= 1.0


def test_kelly_fraction_invalid_inputs(caplog):
    caplog.set_level(logging.WARNING)
    ks = KellySizer(win_rate=-0.5, payoff=0.0)  # invalid
    f = ks.kelly_fraction()
    assert f == 0.0
    assert "Invalid Kelly inputs" in caplog.text


def test_kelly_fraction_exception(monkeypatch, caplog):
    ks = KellySizer(0.6, 2.0, 1.0)
    # Force exception in math
    monkeypatch.setattr(ks, "win_rate", "bad")
    caplog.set_level(logging.ERROR)
    assert ks.kelly_fraction() == 0.0
    assert "Kelly sizing failed" in caplog.text


# ----------------------------------------------------------------------
# size_position
# ----------------------------------------------------------------------

def test_size_position_valid_and_invalid(caplog):
    caplog.set_level(logging.INFO)
    ks = KellySizer(0.6, 2.0, 0.5)
    res = ks.size_position(10000, 100)
    assert isinstance(res, dict)
    assert res["size"] > 0
    assert res["reason"] == "ok"

    # Invalid equity
    res2 = ks.size_position(0, 100)
    assert res2["size"] == 0
    assert res2["reason"] == "invalid_inputs"

    # Invalid price
    res3 = ks.size_position(1000, 0)
    assert res3["size"] == 0
    assert res3["reason"] == "invalid_inputs"


def test_size_position_risk_veto(caplog):
    ks = KellySizer(0.6, 2.0, 0.5)
    res = ks.size_position(10000, 100, risk_veto=True)
    assert res["reason"] == "risk_veto"
    assert res["size"] >= 0


def test_size_position_exception(monkeypatch, caplog):
    ks = KellySizer(0.6, 2.0, 0.5)

    def bad_fraction(*_, **__):
        raise Exception("boom")

    monkeypatch.setattr(ks, "kelly_fraction", bad_fraction)
    caplog.set_level(logging.ERROR)
    res = ks.size_position(1000, 100)
    assert res["size"] == 0
    assert res["reason"] == "exception"
    assert "Kelly sizing failed" in caplog.text


# ----------------------------------------------------------------------
# batch_size
# ----------------------------------------------------------------------

def test_batch_size_multiple_symbols():
    ks = KellySizer(0.6, 2.0, 0.5)
    prices = {"AAPL": 100, "TSLA": 200}
    res = ks.batch_size(10000, prices)
    assert set(res) == {"AAPL", "TSLA"}
    assert all(isinstance(v, dict) for v in res.values())


# ----------------------------------------------------------------------
# update_params, __repr__, save_params
# ----------------------------------------------------------------------

def test_update_and_repr_and_save(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    ks = KellySizer()
    ks.update_params(0.7, 2.5, 0.5, 0.9)
    r = repr(ks)
    assert "KellySizer" in r
    assert "updated" in caplog.text or "KellySizer updated" in caplog.text

    # Save params
    path = tmp_path / "kelly.json"
    ks.save_params(str(path))
    assert os.path.exists(path)
    data = json.load(open(path))
    assert "win_rate" in data and "payoff" in data


def test_save_params_failure(tmp_path, caplog):
    caplog.set_level(logging.ERROR)
    ks = KellySizer()
    # Force failure: pass a directory instead of file
    ks.save_params(str(tmp_path))
    assert "Failed to save KellySizer params" in caplog.text


# ----------------------------------------------------------------------
# _safe_fmt
# ----------------------------------------------------------------------

def test_safe_fmt_success_and_failure():
    assert _safe_fmt(1.234) == "1.23"
    # Pass an object that cannot be cast to float
    class Bad:
        pass
    assert "Bad" in _safe_fmt(Bad())
