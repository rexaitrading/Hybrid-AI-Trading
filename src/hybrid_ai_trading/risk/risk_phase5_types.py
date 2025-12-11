from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Phase5RiskDecision:
    """
    Minimal Phase-5 risk decision object used by tests and guards.

    Fields:
        allowed: True if trade is allowed to proceed
        reason:  short string explaining the primary gate outcome
        details: optional structured information for logging / debugging
    """

    allowed: bool
    reason: str
    details: Dict[str, Any] = field(default_factory=dict)