from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GateScoreThresholds:
    min_signals: int
    min_pnl_samples: int
    min_edge_ratio: float
    min_micro_score: float


def evaluate_thresholds(
    *,
    count_signals: int,
    pnl_samples: int,
    mean_edge_ratio: float,
    mean_micro_score: float,
    thr: GateScoreThresholds,
) -> tuple[bool, str]:
    if count_signals < thr.min_signals:
        return False, "signals_below_min"
    if pnl_samples < thr.min_pnl_samples:
        return False, "pnl_samples_below_min"
    if mean_edge_ratio + 1e-9 < thr.min_edge_ratio:
        return False, "edge_below_min"
    if mean_micro_score + 1e-9 < thr.min_micro_score:
        return False, "micro_below_min"
    return True, "ok"