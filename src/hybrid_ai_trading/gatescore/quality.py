from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .schemas import GateScoreDailySummaryRow


@dataclass(frozen=True)
class GateScoreQualityDecision:
    ok: bool
    reasons: List[str]
    metrics: Dict[str, Any]


def load_thresholds(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    obj = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("thresholds json must be an object")
    return obj


def evaluate_daily_summary_row(
    row: GateScoreDailySummaryRow,
    *,
    thresholds: Dict[str, Any],
    require_real_source: bool = True,
) -> GateScoreQualityDecision:
    """
    Fail-closed quality gate consistent with Block-G semantics:
      - source must be REAL (DEV_REPLAY never arms live readiness)
      - enforce numeric minimums from thresholds["minimums"]
    """
    reasons: List[str] = []
    metrics: Dict[str, Any] = {
        "as_of_date": row.as_of_date,
        "symbol": row.symbol,
        "source": row.source,
        "count_signals": row.count_signals,
        "pnl_samples": row.pnl_samples,
        "mean_edge_ratio": row.mean_edge_ratio,
        "mean_micro_score": row.mean_micro_score,
    }

    if require_real_source and str(row.source).upper() != "REAL":
        reasons.append("source_not_real")

    mins = thresholds.get("minimums") or {}
    try:
        min_signals = int(mins.get("count_signals", 0))
        min_pnl = int(mins.get("pnl_samples", 0))
        min_edge = float(mins.get("mean_edge_ratio", float("-inf")))
        min_micro = float(mins.get("mean_micro_score", float("-inf")))
    except Exception:
        reasons.append("bad_thresholds_minimums")
        return GateScoreQualityDecision(ok=False, reasons=reasons, metrics=metrics)

    if row.count_signals < min_signals:
        reasons.append("count_signals_below_min")
    if row.pnl_samples < min_pnl:
        reasons.append("pnl_samples_below_min")
    if row.mean_edge_ratio < min_edge:
        reasons.append("mean_edge_ratio_below_min")
    if row.mean_micro_score < min_micro:
        reasons.append("mean_micro_score_below_min")

    ok = (len(reasons) == 0)
    return GateScoreQualityDecision(ok=ok, reasons=reasons, metrics=metrics)