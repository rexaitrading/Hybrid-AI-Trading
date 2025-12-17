from __future__ import annotations

from typing import Dict


def scores_to_weights_equal_weight(scores: Dict[str, float]) -> Dict[str, float]:
    """
    No-op allocation: equal weight across provided keys.
    Fail-closed: empty scores => {}.
    """
    keys = list(scores.keys())
    if not keys:
        return {}
    w = 1.0 / float(len(keys))
    return {k: w for k in keys}