from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .allocation import scores_to_weights_equal_weight
from .constraints import PortfolioConstraints


@dataclass(frozen=True)
class OptimizeResult:
    ok: bool
    reasons: List[str]
    weights: Dict[str, float]


class PortfolioOptimizer:
    """
    Phase-7 API surface (v0): equal-weight no-op optimizer, fail-closed.
    """

    def __init__(self, constraints: Optional[PortfolioConstraints] = None, *, fail_closed: bool = True) -> None:
        self.constraints = constraints or PortfolioConstraints()
        self.fail_closed = bool(fail_closed)

    def optimize(self, *, strategy_scores: Dict[str, float]) -> OptimizeResult:
        if not strategy_scores:
            return OptimizeResult(ok=False, reasons=["no_strategy_scores"], weights={})

        weights = scores_to_weights_equal_weight(strategy_scores)
        if not weights:
            return OptimizeResult(ok=False, reasons=["no_weights"], weights={})

        cr = self.constraints.validate(weights)
        if not cr.ok:
            if self.fail_closed:
                return OptimizeResult(ok=False, reasons=cr.reasons, weights={})
            return OptimizeResult(ok=False, reasons=cr.reasons, weights=weights)

        return OptimizeResult(ok=True, reasons=[], weights=weights)