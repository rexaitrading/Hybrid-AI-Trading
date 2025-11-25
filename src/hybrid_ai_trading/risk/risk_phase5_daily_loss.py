"""
Phase-5 daily loss gate helper.

This module contains a pure helper function that applies the
Phase-5 daily loss rule in terms of:

- realized_pnl
- daily_loss_cap
- current position size (pos_qty)
- hypothetical new position size (new_pos_qty)

It returns a Phase5RiskDecision so it can be used by RiskManager
and by tests without wiring the full engine.
"""

from __future__ import annotations

from typing import Any, Dict

from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision


def daily_loss_gate(
    realized_pnl: float,
    daily_loss_cap: float,
    pos_qty: float,
    new_pos_qty: float,
) -> Phase5RiskDecision:
    """
    Apply the Phase-5 daily loss rule.

    Parameters:
        realized_pnl:
            Realized PnL for the current day (negative when losing).
        daily_loss_cap:
            Negative threshold (e.g. -500.0). When realized_pnl is
            <= this value, new risk-increasing trades should be blocked.
        pos_qty:
            Current position quantity (positive long, negative short, 0 flat).
        new_pos_qty:
            Hypothetical position quantity after the proposed trade.

    Rule:

    - If abs(new_pos_qty) > abs(pos_qty), the trade increases exposure.
      In that case:

        * If realized_pnl <= daily_loss_cap:
              BLOCK with reason "daily_loss_cap_block".
        * Else:
              ALLOW with reason "daily_loss_ok".

    - If abs(new_pos_qty) <= abs(pos_qty), the trade reduces or keeps
      exposure flat. In that case we always ALLOW with reason
      "daily_loss_ok_reduce_or_flat".
    """
    realized_pnl = float(realized_pnl or 0.0)
    daily_loss_cap = float(daily_loss_cap or 0.0)
    pos_qty = float(pos_qty or 0.0)
    new_pos_qty = float(new_pos_qty or 0.0)

    increasing = abs(new_pos_qty) > abs(pos_qty)

    details: Dict[str, Any] = {
        "realized_pnl": realized_pnl,
        "daily_loss_cap": daily_loss_cap,
        "pos_qty": pos_qty,
        "new_pos_qty": new_pos_qty,
        "increasing_exposure": increasing,
    }

    if increasing and realized_pnl <= daily_loss_cap:
        return Phase5RiskDecision(
            allowed=False,
            reason="daily_loss_cap_block",
            details=details,
        )

    if increasing:
        return Phase5RiskDecision(
            allowed=True,
            reason="daily_loss_ok",
            details=details,
        )

    # Reducing or keeping exposure flat.
    return Phase5RiskDecision(
        allowed=True,
        reason="daily_loss_ok_reduce_or_flat",
        details=details,
    )