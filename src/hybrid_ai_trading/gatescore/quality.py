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
    """
    Deterministic evaluation for GateScore daily quality.

    Reasons are stable strings for tests/ops:
      - ok
      - signals_below_min
      - pnl_samples_below_min
      - edge_below_min
      - micro_below_min
    """
    if int(count_signals) < int(thr.min_signals):
        return False, "signals_below_min"
    if int(pnl_samples) < int(thr.min_pnl_samples):
        return False, "pnl_samples_below_min"
    if float(mean_edge_ratio) + 1e-12 < float(thr.min_edge_ratio):
        return False, "edge_below_min"
    if float(mean_micro_score) + 1e-12 < float(thr.min_micro_score):
        return False, "micro_below_min"
    return True, "ok"
