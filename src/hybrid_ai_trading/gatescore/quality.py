from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class GateScoreQuality:
    ok: bool
    reason: str = ""
    value: float = 0.0
    min_required: float = 0.0
    samples: int = 0
    min_samples: int = 0


def evaluate_quality(*, value: float, samples: int, min_required: float, min_samples: int) -> GateScoreQuality:
    if samples < int(min_samples):
        return GateScoreQuality(
            ok=False, reason="gatescore_samples_not_ok", value=float(value),
            min_required=float(min_required), samples=int(samples), min_samples=int(min_samples)
        )
    if float(value) < float(min_required):
        return GateScoreQuality(
            ok=False, reason="gatescore_below_threshold", value=float(value),
            min_required=float(min_required), samples=int(samples), min_samples=int(min_samples)
        )
    return GateScoreQuality(
        ok=True, reason="gatescore_ok", value=float(value),
        min_required=float(min_required), samples=int(samples), min_samples=int(min_samples)
    )


def load_thresholds_from_contract(status: Dict[str, Any]) -> tuple[float, int]:
    # Contract keys already exist in your Block-G status stub builder
    return float(status.get("gatescore_min_required", 0.0) or 0.0), int(status.get("gatescore_min_samples", 0) or 0)