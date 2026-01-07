from __future__ import annotations

import os

def _env_bps(name: str, default: float) -> float:
    try:
        v = os.getenv(name, "").strip()
        if not v:
            return float(default)
        return float(v)
    except Exception:
        return float(default)
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
    sbps = float(inp.spread_bps)
    cbps = float(inp.commission_bps)
    lbps = float(inp.slippage_bps)

    # If caller left all zeros, allow env-configured defaults (realism) without breaking correctness.
    if (sbps == 0.0 and cbps == 0.0 and lbps == 0.0):
        sbps = _env_bps("HAT_SPREAD_BPS", 0.0)
        cbps = _env_bps("HAT_COMMISSION_BPS", 0.0)
        lbps = _env_bps("HAT_SLIPPAGE_BPS", 0.0)

    tbps = sbps + cbps + lbps
    cost = n * (tbps / 10000.0)
    eff = n - cost
    return CostEstimate(total_bps=tbps, total_cost=cost, effective_notional=eff)
