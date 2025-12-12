"""
Phase-5 account-wide daily caps helper.

This helper is meant to guard the *entire account* (all symbols),
not just a single symbol slice like SPY ORB or NVDA B+.

It takes:
- account_realized_pnl: realized PnL for the account (USD or base currency)
- account_daily_loss_cap: negative threshold (e.g. -1000.0)

and returns a Phase5RiskDecision.
"""

from __future__ import annotations

from typing import Any, Dict

from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision


def account_daily_loss_gate(
    account_realized_pnl: float,
    account_daily_loss_cap: float,
) -> Phase5RiskDecision:
    """
    Account-wide daily loss cap.

    - If account_realized_pnl <= account_daily_loss_cap:
        BLOCK with reason "account_daily_loss_cap_block".
    - Else:
        ALLOW with reason "account_daily_loss_ok".
    """
    account_realized_pnl = float(account_realized_pnl or 0.0)
    account_daily_loss_cap = float(account_daily_loss_cap or 0.0)

    details: Dict[str, Any] = {
        "account_realized_pnl": account_realized_pnl,
        "account_daily_loss_cap": account_daily_loss_cap,
    }

    if account_realized_pnl <= account_daily_loss_cap:
        return Phase5RiskDecision(
            allowed=False,
            reason="account_daily_loss_cap_block",
            details=details,
        )

    return Phase5RiskDecision(
        allowed=True,
        reason="account_daily_loss_ok",
        details=details,
    )# --- Phase-5 override: simplified account_daily_loss_gate --------------------

def account_daily_loss_gate(
    realized_pnl: float,
    account_daily_loss_cap: float,
):
    """
    Simplified account-level daily loss gate for Phase-5.

    Behavior:
    - If account_daily_loss_cap <= 0: treat as not configured (pass-through).
    - If realized_pnl <= -abs(account_daily_loss_cap): block with reason
      "account_daily_loss_cap_block".
    - Otherwise: allow with reason "account_daily_loss_cap_ok".
    """
    from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision

    rpnl = float(realized_pnl)
    cap = float(account_daily_loss_cap)

    details = {
        "account_realized_pnl": rpnl,
        "account_daily_loss_cap": cap,
    }

    if cap <= 0.0:
        return Phase5RiskDecision(
            allowed=True,
            reason="account_daily_loss_cap_not_configured",
            details=details,
        )

    if rpnl <= -abs(cap):
        return Phase5RiskDecision(
            allowed=False,
            reason="account_daily_loss_cap_block",
            details=details,
        )

    return Phase5RiskDecision(
        allowed=True,
        reason="account_daily_loss_cap_ok",
        details=details,
    )
# --- End Phase-5 override ----------------------------------------------------
