"""
Unit Tests: KellySizer (Hybrid AI Quant Pro v8.0 – Absolute 100% Coverage)
--------------------------------------------------------------------------
Covers:
- Initialization (defaults + custom)
- Optimal fraction (valid, invalid, exception)
- Kelly fraction (scaled, clamped, exception)
- size_position (valid, invalid equity/price, exception)
- update_params
- __repr__ correctness
"""

import logging
import pytest
from hybrid_ai_trading.risk.kelly_sizer import KellySizer


def test_init_defaults_and_custom(caplog):
    caplog.set_level(logging.INFO)
    d1 = KellySizer()
    d2 = KellySizer(0.6, 2.0, 0.5)
    assert isinstance(d1, KellySizer)
    assert isinstance(d2, KellySizer)
    assert "KellySizer initialized" in caplog.text


def test_optimal_fraction_valid_invalid(monkeypatch, caplog):
    ks = KellySizer(0.6, 2.0, 1.0)
    assert ks.optimal_fraction() > 0

    ks.payoff = 0  # invalid
    assert ks.optimal_fraction() == 0.0

    ks.payoff = float("inf")  # invalid payoff
    assert ks.optimal_fraction() == 0.0

    ks.win_rate = -1  # invalid win_rate
    assert ks.optimal_fraction() == 0.0

    monkeypatch.setattr("math.isinf", lambda _: True)  # force invalid
    assert ks.optimal_fraction() == 0.0

    # Exception branch
    def bad_method(x): raise Exception("boom")
    monkeypatch.setattr("math.isinf", bad_method)
    assert ks.optimal_fraction() == 0.0
    assert "Kelly optimal fraction failed" in caplog.text


def test_kelly_fraction_scaled_and_clamped(caplog):
    caplog.set_level(logging.DEBUG)
    ks = KellySizer(0.6, 2.0, 0.5)
    f = ks.kelly_fraction()
    assert 0 <= f <= 1
    assert "Scaled Kelly fraction" in caplog.text

    # Extreme scaling → clamp
    ks.fraction = 10.0
    f2 = ks.kelly_fraction()
    assert f2 <= 1.0


def test_kelly_fraction_exception(monkeypatch, caplog):
    ks = KellySizer(0.6, 2.0, 1.0)
    monkeypatch.setattr(ks, "optimal_fraction", lambda: (_ for _ in ()).throw(Exception("boom")))
    assert ks.kelly_fraction() == 0.0
    assert "Kelly sizing failed" in caplog.text


def test_size_position_valid_and_invalid(caplog):
    caplog.set_level(logging.INFO)
    ks = KellySizer(0.6, 2.0, 0.5)
    size = ks.size_position(10000, 100)
    assert size > 0
    assert "Position sizing" in caplog.text

    # Invalid equity
    assert ks.size_position(0, 100) == 0.0
    # Invalid price
    assert ks.size_position(1000, 0) == 0.0


def test_size_position_exception(monkeypatch, caplog):
    ks = KellySizer(0.6, 2.0, 0.5)

    def bad_fraction(): raise Exception("boom")
    monkeypatch.setattr(ks, "kelly_fraction", bad_fraction)

    assert ks.size_position(1000, 100) == 0.0
    assert "Kelly sizing position failed" in caplog.text


def test_update_and_repr(caplog):
    ks = KellySizer()
    ks.update_params(0.7, 2.5, 0.5)
    r = repr(ks)
    assert "KellySizer" in r
    assert "updated" in caplog.text or "KellySizer updated" in caplog.text
