from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable


@dataclass(frozen=True)
class Allocation:
    """Portfolio allocation weights that should sum to 1.0 (Phase-7 scaffold)."""
    weights: Dict[str, float]


def allocate_equal_weight(symbols: Iterable[str]) -> Allocation:
    syms = [str(s).strip() for s in symbols if str(s).strip()]
    if not syms:
        return Allocation(weights={})
    w = 1.0 / float(len(syms))
    return Allocation(weights={s: w for s in syms})