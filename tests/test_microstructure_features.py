from __future__ import annotations

import math

import pytest

from hybrid_ai_trading.microstructure import compute_microstructure_features


def test_compute_microstructure_features_returns_expected_fields():
    # Simple deterministic series: flat then small up move
    # We avoid any external data dependency (unit test only).
    prices = [100.0, 100.0, 100.1, 100.1, 100.2]

    out = compute_microstructure_features(prices)

    # Required keys used by Phase-2 snapshot/exporters
    assert isinstance(out, dict)
    assert "ms_range_pct" in out
    assert "ms_trend_flag" in out

    # Types and invariants
    assert isinstance(out["ms_range_pct"], (int, float))
    assert isinstance(out["ms_trend_flag"], int)

    assert out["ms_range_pct"] >= 0.0
    assert out["ms_trend_flag"] in (-1, 0, 1)


def test_compute_microstructure_features_handles_short_series():
    # Should not crash; should return sensible defaults
    out = compute_microstructure_features([100.0])
    assert isinstance(out, dict)
    assert "ms_range_pct" in out
    assert "ms_trend_flag" in out
    assert out["ms_range_pct"] >= 0.0
    assert out["ms_trend_flag"] in (-1, 0, 1)


def test_ms_range_pct_is_finite():
    out = compute_microstructure_features([100.0, 100.0, 100.0, 100.0])
    assert math.isfinite(float(out["ms_range_pct"]))