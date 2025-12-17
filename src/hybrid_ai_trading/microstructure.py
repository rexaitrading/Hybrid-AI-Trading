from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class MicrostructureFeatures:
    volume_sum: float


def compute_microstructure_features(*, closes: List[float], volumes: List[float]) -> MicrostructureFeatures:
    """
    Minimal deterministic microstructure features (scaffold).
    """
    vsum = float(sum(float(v) for v in volumes))
    return MicrostructureFeatures(volume_sum=vsum)