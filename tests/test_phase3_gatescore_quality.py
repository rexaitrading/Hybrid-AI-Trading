from hybrid_ai_trading.gatescore.quality import evaluate_quality


def test_quality_blocks_low_samples():
    q = evaluate_quality(value=1.0, samples=1, min_required=0.5, min_samples=10)
    assert q.ok is False
    assert q.reason == "gatescore_samples_not_ok"


def test_quality_blocks_low_value():
    q = evaluate_quality(value=0.1, samples=10, min_required=0.5, min_samples=10)
    assert q.ok is False
    assert q.reason == "gatescore_below_threshold"


def test_quality_ok():
    q = evaluate_quality(value=0.8, samples=20, min_required=0.5, min_samples=10)
    assert q.ok is True
    assert q.reason == "gatescore_ok"