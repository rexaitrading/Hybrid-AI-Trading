from __future__ import annotations

from hybrid_ai_trading.gatescore.quality import evaluate_daily_summary_row
from hybrid_ai_trading.gatescore.schemas import GateScoreDailySummaryRow


def test_gatescore_quality_fail_closed_on_non_real_source():
    row = GateScoreDailySummaryRow(
        as_of_date="2025-12-15",
        symbol="NVDA",
        source="DEV_REPLAY",
        count_signals=999,
        pnl_samples=999,
        mean_edge_ratio=1.0,
        mean_micro_score=1.0,
    )
    thresholds = {"minimums": {"count_signals": 10, "pnl_samples": 10, "mean_edge_ratio": 0.0, "mean_micro_score": 0.0}}
    dec = evaluate_daily_summary_row(row, thresholds=thresholds, require_real_source=True)
    assert dec.ok is False
    assert "source_not_real" in dec.reasons


def test_gatescore_quality_passes_when_meeting_thresholds():
    row = GateScoreDailySummaryRow(
        as_of_date="2025-12-15",
        symbol="NVDA",
        source="REAL",
        count_signals=115,
        pnl_samples=375,
        mean_edge_ratio=0.10,
        mean_micro_score=0.20,
    )
    thresholds = {"minimums": {"count_signals": 10, "pnl_samples": 10, "mean_edge_ratio": 0.0, "mean_micro_score": 0.0}}
    dec = evaluate_daily_summary_row(row, thresholds=thresholds, require_real_source=True)
    assert dec.ok is True
    assert dec.reasons == []