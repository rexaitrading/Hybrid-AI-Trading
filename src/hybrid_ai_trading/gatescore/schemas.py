from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class GateScoreDailySummaryRow:
    as_of_date: str
    symbol: str
    source: str
    count_signals: int
    pnl_samples: int
    mean_edge_ratio: float
    mean_micro_score: float

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "GateScoreDailySummaryRow":
        return GateScoreDailySummaryRow(
            as_of_date=str(d.get("as_of_date") or "").strip(),
            symbol=str(d.get("symbol") or "").strip(),
            source=str(d.get("source") or "").strip(),
            count_signals=int(d.get("count_signals")),
            pnl_samples=int(d.get("pnl_samples")),
            mean_edge_ratio=float(d.get("mean_edge_ratio")),
            mean_micro_score=float(d.get("mean_micro_score")),
        )


@dataclass(frozen=True)
class GateScoreEventRow:
    ts_utc: str
    symbol: str
    event_type: str
    ok: bool
    reasons: str
    metrics: Optional[Dict[str, Any]] = None