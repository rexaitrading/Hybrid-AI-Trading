from __future__ import annotations

from pathlib import Path

from hybrid_ai_trading.portfolio.logging import write_daily_summary


def test_phase6_write_daily_summary_one_row(tmp_path: Path):
    out = tmp_path / "phase6_daily_summary.csv"
    rows = [{"as_of_date": "2025-12-17", "strategy_id": "NVDA_BPLUS", "score": 0.5}]
    write_daily_summary(rows=rows, path=str(out))

    txt = out.read_text(encoding="utf-8")
    assert "as_of_date" in txt
    assert "strategy_id" in txt
    assert "NVDA_BPLUS" in txt