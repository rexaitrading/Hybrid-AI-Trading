from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GateScoreDailyRow:
    as_of_date: str
    symbol: str
    count_signals: int = 0
    pnl_samples: int = 0
    mean_edge_ratio: float = 0.0
    mean_micro_score: float = 0.0


@dataclass(frozen=True)
class GateScoreEvent:
    ts_utc: str
    symbol: str
    event: str
    detail: str = ""
    value: Optional[float] = None
