"""
Phase-5 account-level caps (daily loss gate).

NVDA runner expects:
- account_daily_loss_gate(account_realized_pnl=..., account_daily_loss_cap=...)
- return object with attributes: allowed (bool), reason (str), details (dict|None)

Conservative behavior:
- If realized pnl <= -abs(cap) -> BLOCK
- Else -> ALLOW
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class AccountGateDecision:
    allowed: bool
    reason: str
    details: Optional[Dict[str, Any]] = None


def account_daily_loss_gate(
    account_realized_pnl: float,
    account_daily_loss_cap: float,
    **kwargs,
) -> AccountGateDecision:
    # Normalize inputs
    try:
        pnl = float(account_realized_pnl)
    except Exception:
        pnl = 0.0

    try:
        cap = float(account_daily_loss_cap)
    except Exception:
        cap = 0.0

    # Cap convention: negative means max loss (e.g., -500). If user passes +50, treat as -50.
    cap_loss = -abs(cap) if cap != 0.0 else 0.0

    if cap_loss != 0.0 and pnl <= cap_loss:
        return AccountGateDecision(
            allowed=False,
            reason="ACCOUNT_DAILY_LOSS_CAP_BREACH",
            details={"account_realized_pnl": pnl, "account_daily_loss_cap": cap_loss},
        )

    return AccountGateDecision(
        allowed=True,
        reason="ACCOUNT_DAILY_LOSS_OK",
        details={"account_realized_pnl": pnl, "account_daily_loss_cap": cap_loss},
    )