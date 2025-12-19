from __future__ import annotations

from pathlib import Path

from hybrid_ai_trading.gatescore.quality import load_thresholds


def test_load_thresholds_accepts_utf8_bom(tmp_path: Path):
    p = tmp_path / "thresholds.json"
    # write BOM-prefixed JSON bytes
    data = b"\xef\xbb\xbf" + b'{"minimums": {"count_signals": 1, "pnl_samples": 1, "mean_edge_ratio": 0.0, "mean_micro_score": 0.0}}'
    p.write_bytes(data)

    obj = load_thresholds(str(p))
    assert "minimums" in obj