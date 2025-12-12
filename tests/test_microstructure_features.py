from __future__ import annotations

import math

from hybrid_ai_trading.microstructure import compute_microstructure_features


def _vols(n: int) -> list[float]:
    # deterministic non-zero volumes
    return [1000.0] * n


def test_compute_microstructure_features_returns_expected_fields():
    prices = [100.0, 100.0, 100.1, 100.1, 100.2]
    vols   = _vols(len(prices))

    out = compute_microstructure_features(prices, vols)

    assert isinstance(out, dict)
    assert "ms_range_pct" in out
    assert "ms_trend_flag" in out

    assert isinstance(out["ms_range_pct"], (int, float))
    assert isinstance(out["ms_trend_flag"], int)

    assert float(out["ms_range_pct"]) >= 0.0
    assert out["ms_trend_flag"] in (-1, 0, 1)


def test_compute_microstructure_features_handles_short_series():
    prices = [100.0]
    vols   = _vols(len(prices))

    out = compute_microstructure_features(prices, vols)

    assert isinstance(out, dict)
    assert "ms_range_pct" in out
    assert "ms_trend_flag" in out
    assert float(out["ms_range_pct"]) >= 0.0
    assert out["ms_trend_flag"] in (-1, 0, 1)


def test_ms_range_pct_is_finite():
    prices = [100.0, 100.0, 100.0, 100.0]
    vols   = _vols(len(prices))

    out = compute_microstructure_features(prices, vols)
    assert math.isfinite(float(out["ms_range_pct"]))