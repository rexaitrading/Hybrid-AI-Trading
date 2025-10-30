from typing import Any, Dict


def compute_risk_cap(
    netliq_cad: float,
    daily_target: float = 0.007,  # 0.7% goal
    allocation: float = 0.5,  # portion to this trade
    max_cap_frac: float = 0.02,
) -> Dict[str, Any]:
    """
    Returns risk_cap_cad bounded by max_cap_frac of NetLiq.
    """
    target_budget = (
        max(0.0, float(netliq_cad)) * max(0.0, daily_target) * max(0.0, allocation)
    )
    cap_limit = float(netliq_cad) * max(0.0, max_cap_frac)
    rc = min(target_budget, cap_limit)
    return {
        "risk_cap_cad": rc,
        "daily_target": daily_target,
        "allocation": allocation,
        "max_cap_frac": max_cap_frac,
    }
