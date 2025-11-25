"""
Phase-5 risk types.

This module defines narrow, explicit types used by Phase-5 risk logic:

- Phase5RiskDecision: the result of a Phase-5 risk check for a single trade.

The intent is that:

- RiskManager (or any risk backend) returns Phase5RiskDecision from
  a method such as `check_trade_phase5(trade: Dict[str, Any])`.
- Phase5RiskAdapter can then convert that decision into the flat
  JSON/CSV/Notion fields used by the Phase-5 runners.

Keeping this as a small, focused module helps keep the Phase-5 wiring
clear and testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Phase5RiskDecision:
    """
    Result of Phase-5 risk evaluation for a single proposed trade.

    Fields:
        allowed:
            True if the trade passes all configured Phase-5 risk rules
            (daily loss, MDD, no-averaging-down, cooldown, etc.).
        reason:
            Short, machine-readable reason string such as:

            - "phase5_risk_ok"
            - "daily_loss_cap_block"
            - "mdd_cap_block"
            - "no_averaging_down_long_block"

            This is what ultimately flows into `phase5_risk_reason`
            and contributes to `phase5_combined_reason` in JSONL / Notion.
        details:
            Optional extra diagnostics (numbers, flags, thresholds) that
            are useful for logging or debugging but not required by the
            main engine. For example:

            {
                "source": "daily_loss",
                "current_pnl": -350.0,
                "projected_pnl": -520.0,
            }
    """

    allowed: bool
    reason: str
    details: Dict[str, Any]