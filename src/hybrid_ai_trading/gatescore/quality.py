from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .schemas import GateScoreDailySummaryRow
def _mins_for_symbol(thresholds: Dict[str, Any], symbol: str) -> Dict[str, Any]:
    """
    Support two threshold schemas:
      A) {"minimums": {"count_signals":..., "pnl_samples":..., "mean_edge_ratio":..., "mean_micro_score":...}}
      B) {"NVDA": {"min_signals":..., "min_pnl_samples":..., "min_edge_ratio":..., "min_micro_score":...}, "DEFAULT": {...}}
    """
    mins = thresholds.get("minimums")
    if isinstance(mins, dict):
        return mins

    sym = str(symbol or "").upper()
    bucket = thresholds.get(sym) or thresholds.get("DEFAULT") or {}
    if not isinstance(bucket, dict):
        return {}

    return {
        "count_signals": bucket.get("min_signals", 0),
        "pnl_samples": bucket.get("min_pnl_samples", 0),
        "mean_edge_ratio": bucket.get("min_edge_ratio", float("-inf")),
        "mean_micro_score": bucket.get("min_micro_score", float("-inf")),
    }



@dataclass(frozen=True)
class GateScoreQualityDecision:
    ok: bool
    reasons: List[str]
    metrics: Dict[str, Any]


def load_thresholds(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    obj = json.loads(p.read_text(encoding="utf-8-sig"))
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

    mins = _mins_for_symbol(thresholds, row.symbol) or {}
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