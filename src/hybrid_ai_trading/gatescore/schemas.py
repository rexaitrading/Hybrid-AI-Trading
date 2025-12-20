from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GateScoreDailyRow:
    as_of_date: str
    symbol: str
    count_signals: int
    pnl_samples: int
    mean_edge_ratio: float
    mean_micro_score: float
    mean_pnl: float