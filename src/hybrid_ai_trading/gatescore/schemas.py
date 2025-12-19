from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GateScoreDailySummaryRow:
    as_of_date: str
    symbol: str
    gatescore_value: float
    gatescore_samples: int
    producer: str = "unknown"
    ok_today: bool = False
    reason: str = ""


@dataclass(frozen=True)
class GateScoreEventRow:
    ts: str
    as_of_date: str
    symbol: str
    event: str
    value: float
    meta: Optional[str] = None