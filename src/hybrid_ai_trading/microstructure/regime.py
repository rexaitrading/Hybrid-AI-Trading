from __future__ import annotations

def classify_micro_regime(ms_range_pct: float, spread_bps: float, fee_bps: float) -> str:
    # deterministic, simple
    if ms_range_pct >= 0.02 or spread_bps >= 2.0 or fee_bps >= 2.0:
        return "RED"
    if ms_range_pct >= 0.006 or spread_bps >= 0.8 or fee_bps >= 0.8:
        return "CAUTION"
    return "GREEN"