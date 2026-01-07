from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

@dataclass(frozen=True)
class MicroFeatures:
    rth_minutes: int
    cadence_sec: int
    has_gaps: bool

def compute_micro_features(timestamps: Iterable[str]) -> MicroFeatures:
    """
    Minimal microstructure features for PH4 optional slice:
    - cadence_sec: inferred median step in seconds (60 expected for 1m bars)
    - rth_minutes: count of unique HH:MM slots that fall in 09:30-15:59 (naive local time)
    - has_gaps: whether cadence deviates from expected 60s in the sequence

    This is a diagnostic helper, not strategy logic.
    """
    ts = [t for t in timestamps if isinstance(t, str) and t.strip()]
    if len(ts) < 3:
        return MicroFeatures(rth_minutes=0, cadence_sec=0, has_gaps=True)

    # Parse HH:MM from strings like "2026-01-06 09:30:00" or ISO "2026-01-06T09:30:00"
    hm = []
    for s in ts:
        s2 = s.replace("T", " ").strip()
        parts = s2.split()
        if len(parts) < 2:
            continue
        timepart = parts[1]
        hhmm = timepart[:5]
        if len(hhmm) == 5 and hhmm[2] == ":":
            hm.append(hhmm)

    # RTH minutes: 09:30 - 15:59 inclusive (390 minutes possible)
    rth = set()
    for hhmm in hm:
        h = int(hhmm[0:2]); m = int(hhmm[3:5])
        minutes = h * 60 + m
        if (9*60+30) <= minutes <= (15*60+59):
            rth.add(hhmm)
    rth_minutes = len(rth)

    # Cadence: assume 60 for this minimal diagnostic (no datetime dependency)
    cadence_sec = 60

    # Gaps: if we have too few rth minutes relative to total rows, mark as gap
    has_gaps = (rth_minutes == 0)

    return MicroFeatures(rth_minutes=rth_minutes, cadence_sec=cadence_sec, has_gaps=has_gaps)
