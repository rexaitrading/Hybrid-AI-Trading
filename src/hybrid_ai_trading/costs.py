from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostInputs:
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
    Deterministic, test-driven cost estimator.
    total_bps = spread + commission + slippage
    total_cost = notional * total_bps/10000
    effective_notional = notional - total_cost
    """
    n = float(notional)
    tbps = float(inp.spread_bps) + float(inp.commission_bps) + float(inp.slippage_bps)
    cost = n * (tbps / 10000.0)
    eff = n - cost
    return CostEstimate(total_bps=tbps, total_cost=cost, effective_notional=eff)
