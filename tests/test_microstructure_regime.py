from __future__ import annotations

from hybrid_ai_trading.microstructure.regime import classify_micro_regime


def test_micro_regime_green():
    assert classify_micro_regime(0.002, 0.4, 0.4) == "GREEN"


def test_micro_regime_caution():
    assert classify_micro_regime(0.006, 0.8, 0.8) == "CAUTION"


def test_micro_regime_red():
    assert classify_micro_regime(0.02, 2.0, 2.0) == "RED"