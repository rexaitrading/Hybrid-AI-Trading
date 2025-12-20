from __future__ import annotations

from hybrid_ai_trading.gatescore.quality import GateScoreThresholds, evaluate_thresholds


def test_gatescore_quality_ok():
    ok, reason = evaluate_thresholds(
        count_signals=200,
        pnl_samples=400,
        mean_edge_ratio=0.05,
        mean_micro_score=0.7,
        thr=GateScoreThresholds(100, 300, 0.03, 0.55),
    )
    assert ok is True
    assert reason == "ok"


def test_gatescore_quality_fails_edge():
    ok, reason = evaluate_thresholds(
        count_signals=200,
        pnl_samples=400,
        mean_edge_ratio=0.01,
        mean_micro_score=0.7,
        thr=GateScoreThresholds(100, 300, 0.03, 0.55),
    )
    assert ok is False
    assert reason == "edge_below_min"