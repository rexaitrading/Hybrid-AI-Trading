from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class PortfolioRiskDecision:
    ok: bool
    reasons: List[str]


def check_portfolio_risk(
    *,
    portfolio_state: Dict,
    proposed_intent: Dict,
    daily_loss_cap: Optional[float] = None,
    max_gross_notional: Optional[float] = None,
) -> PortfolioRiskDecision:
    """
    Phase-6 scaffold: global portfolio checks.
    Fail-closed reasons must be explicit.
    """
    reasons: List[str] = []

    # Example: daily loss cap
    if daily_loss_cap is not None:
        pnl = float(portfolio_state.get("day_realized_pnl", 0.0) or 0.0)
        if pnl <= float(daily_loss_cap):
            reasons.append("PORTFOLIO_DAILY_LOSS_CAP")

    # Example: gross exposure cap
    if max_gross_notional is not None:
        gross = float(portfolio_state.get("gross_notional", 0.0) or 0.0)
        add = float(proposed_intent.get("notional", 0.0) or 0.0)
        if (gross + abs(add)) > float(max_gross_notional):
            reasons.append("PORTFOLIO_MAX_GROSS")

    if reasons:
        return PortfolioRiskDecision(ok=False, reasons=reasons)
    return PortfolioRiskDecision(ok=True, reasons=["OK"])