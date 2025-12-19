from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ConstraintResult:
    ok: bool
    reasons: List[str]


@dataclass(frozen=True)
class PortfolioConstraints:
    """
    Phase-7 placeholders (fail-closed in optimizer if constraints fail).
    """
    max_gross_exposure: float = 1.0
    max_single_name: float = 0.25

    def validate(self, weights: Dict[str, float]) -> ConstraintResult:
        reasons: List[str] = []
        gross = sum(abs(v) for v in weights.values())
        if gross > float(self.max_gross_exposure) + 1e-9:
            reasons.append("gross_exposure_exceeds_limit")

        for k, v in weights.items():
            if abs(v) > float(self.max_single_name) + 1e-9:
                reasons.append(f"single_name_exceeds_limit:{k}")

        return ConstraintResult(ok=(len(reasons) == 0), reasons=reasons)