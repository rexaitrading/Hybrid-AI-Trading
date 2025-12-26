from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class CostGateDecision:
    ok: bool
    reason: str = ""
    details: Optional[Dict[str, Any]] = None


def estimate_total_cost_pct(*, cfg: Dict[str, Any]) -> float:
    """
    Phase-2 minimal cost estimator.

    Inputs (pct are fractions, e.g. 0.001 = 0.1%):
      - slippage_pct
      - commission_pct
      - optional latency_ms * latency_penalty_per_ms
    """
    slip = float(cfg.get("slippage_pct", 0.0) or 0.0)
    comm = float(cfg.get("commission_pct", 0.0) or 0.0)

    lat_ms = float(cfg.get("latency_ms", 0.0) or 0.0)
    lat_pen = float(cfg.get("latency_penalty_per_ms", 0.0) or 0.0) * lat_ms

    return max(0.0, slip + comm + lat_pen)


def evaluate_cost_gate(*, cfg: Dict[str, Any]) -> CostGateDecision:
    """
    Phase-2 cost/latency gate.

    Safety:
      - disabled by default (enabled=False => ok=True)
      - if enabled=True and est_total_cost_pct > max_total_cost_pct => ok=False (fail-closed)

    Expected cfg keys:
      enabled: bool (default False)
      max_total_cost_pct: float
      slippage_pct: float
      commission_pct: float
      latency_ms: float
      latency_penalty_per_ms: float
    """
    if not bool(cfg.get("enabled", False)):
        return CostGateDecision(ok=True, reason="cost_gate_disabled")

    max_cost = cfg.get("max_total_cost_pct", None)
    est = estimate_total_cost_pct(cfg=cfg)

    if max_cost is not None and est > float(max_cost):
        return CostGateDecision(
            ok=False,
            reason="cost_too_high",
            details={"est_total_cost_pct": est, "max_total_cost_pct": float(max_cost)},
        )

    return CostGateDecision(ok=True, reason="cost_gate_ok", details={"est_total_cost_pct": est})