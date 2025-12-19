from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


class OptimizerNotReady(RuntimeError):
    """Raised when optimizer is enabled but not implemented (fail-closed)."""


@dataclass
class OptimizerResult:
    ok: bool
    weights: Optional[Dict[str, float]] = None
    reason: str = ""


def optimize_portfolio(*, inputs: Dict[str, Any], cfg: Dict[str, Any]) -> OptimizerResult:
    """
    Phase-7 optimizer interface.

    Safety rules:
      - disabled by default
      - if enabled=True but no implementation -> raise OptimizerNotReady (fail-closed)
    """
    if not bool(cfg.get("enabled", False)):
        return OptimizerResult(ok=False, weights=None, reason="optimizer_disabled")

    raise OptimizerNotReady("optimizer_enabled_but_not_implemented")