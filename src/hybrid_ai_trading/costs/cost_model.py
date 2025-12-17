from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CostInputs:
    """
    Minimal deterministic cost inputs (Phase-2 scaffold).

    spread_bps: estimated spread in basis points (bps)
    commission_bps: commission in bps (optional)
    slippage_bps: slippage in bps (optional)
    """
    spread_bps: float = 0.0
    commission_bps: float = 0.0
    slippage_bps: float = 0.0


@dataclass(frozen=True)
class CostEstimate:
    total_bps: float
    total_cost: float
    effective_notional: float


def estimate_costs(*, notional: float, inp: CostInputs) -> CostEstimate:
    """
    Deterministic cost estimate:
      total_bps = spread + commission + slippage
      total_cost = notional * total_bps / 10_000
      effective_notional = notional - total_cost
    """
    n = float(notional or 0.0)
    if n <= 0.0:
        return CostEstimate(total_bps=0.0, total_cost=0.0, effective_notional=0.0)

    total_bps = float(inp.spread_bps or 0.0) + float(inp.commission_bps or 0.0) + float(inp.slippage_bps or 0.0)
    total_cost = n * (total_bps / 10_000.0)
    return CostEstimate(total_bps=total_bps, total_cost=total_cost, effective_notional=(n - total_cost))