from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


class OptimizerNotReady(RuntimeError):
    pass


@dataclass(frozen=True)
class OptimizerOutput:
    ok: bool
    reason: str
    weights: Dict[str, float]


def optimize_portfolio(*, inputs: Dict[str, Any], cfg: Dict[str, Any]) -> OptimizerOutput:
    """
    Phase-7 optimizer entrypoint (paper-first, fail-closed).

    Contract (current tests):
      - enabled=False -> safe no-op with ok=False, reason="optimizer_disabled"
      - enabled=True  -> raise OptimizerNotReady (until full Phase-7 wiring is completed)

    Future wiring will:
      - read Phase6 summary + BlockG status
      - enforce Block-G for live intent
      - emit deterministic weights artifacts
    """
    enabled = bool(cfg.get("enabled", False))
    if not enabled:
        return OptimizerOutput(ok=False, reason="optimizer_disabled", weights={})

    # Fail-closed until full optimizer pipeline is wired into Phase6/BlockG.
    raise OptimizerNotReady("phase7 optimizer not armed (paper-first scaffold)")
