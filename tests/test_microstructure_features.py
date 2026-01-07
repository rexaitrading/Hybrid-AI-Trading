from hybrid_ai_trading.microstructure.features import compute_micro_features, MicroFeatures

def test_compute_micro_features_basic_rth_count():
    # 3 RTH minutes
    ts = [
        "2026-01-06 09:30:00",
        "2026-01-06 09:31:00",
        "2026-01-06 09:32:00",
    ]
    out = compute_micro_features(ts)
    assert isinstance(out, MicroFeatures)
    assert out.cadence_sec == 60
    assert out.rth_minutes == 3
    assert out.has_gaps is False

def test_compute_micro_features_empty_is_gap():
    out = compute_micro_features([])
    assert out.has_gaps is True
