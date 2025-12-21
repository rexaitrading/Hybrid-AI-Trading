# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class MicroCostSnapshot:
    avg_cost_bps: float = 0.0
    slippage_bps: float = 0.0
    commission_bps: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "avg_cost_bps": float(self.avg_cost_bps),
            "slippage_bps": float(self.slippage_bps),
            "commission_bps": float(self.commission_bps),
        }


def default_snapshot() -> MicroCostSnapshot:
    return MicroCostSnapshot()
