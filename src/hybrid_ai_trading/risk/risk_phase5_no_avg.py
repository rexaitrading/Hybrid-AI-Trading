"""
Phase-5 no-averaging-down gate helper.

This module contains a pure helper function that applies the Phase-5
no-averaging-down rule in terms of:

- current position quantity (pos_qty)
- current average price (avg_price)
- proposed side / qty / price

It returns a Phase5RiskDecision so it can be used by RiskManager and by
tests without wiring the full engine.
"""

from __future__ import annotations

from typing import Any, Dict

from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision


def no_averaging_down_gate(
    side: str,
    qty: float,
    price: float,
    pos_qty: float,
    avg_price: float,
) -> Phase5RiskDecision:
    """
    Apply the Phase-5 no-averaging-down rule.

    Definitions:
        - Long position: pos_qty > 0
          Averaging down if we BUY/LONG more at a LOWER price than avg_price.
        - Short position: pos_qty < 0
          Averaging down if we SELL/SHORT more at a HIGHER price than avg_price.
        - Flat (pos_qty == 0):
          No averaging-down possible; always allowed.

    Parameters:
        side:
            Proposed trade side string ("BUY", "SELL", "LONG", "SHORT" etc.).
        qty:
            Proposed trade quantity (> 0 for adding, 0 or <0 treated as non-risk).
        price:
            Proposed trade price.
        pos_qty:
            Current position quantity (positive long, negative short, 0 flat).
        avg_price:
            Current average price of the open position.

    Returns:
        Phase5RiskDecision:
            allowed=True/False, reason string, and diagnostics in details.
    """
    side_raw = (side or "").upper()
    qty = float(qty or 0.0)
    price = float(price or 0.0)
    pos_qty = float(pos_qty or 0.0)
    avg_price = float(avg_price or 0.0)

    details: Dict[str, Any] = {
        "side": side_raw,
        "qty": qty,
        "price": price,
        "pos_qty": pos_qty,
        "avg_price": avg_price,
    }

    # Flat: cannot average down.
    if pos_qty == 0.0 or qty <= 0.0:
        return Phase5RiskDecision(
            allowed=True,
            reason="no_avg_ok_flat_or_nonpositive_qty",
            details=details,
        )

    # Long position case.
    if pos_qty > 0.0:
        if "BUY" in side_raw or "LONG" in side_raw:
            if price < avg_price:
                details["direction"] = "long"
                return Phase5RiskDecision(
                    allowed=False,
                    reason="no_averaging_down_long_block",
                    details=details,
                )
        # Any other action from a long perspective is fine for this gate.
        details["direction"] = "long"
        return Phase5RiskDecision(
            allowed=True,
            reason="no_avg_ok_long",
            details=details,
        )

    # Short position case (pos_qty < 0).
    if "SELL" in side_raw or "SHORT" in side_raw:
        if price > avg_price:
            details["direction"] = "short"
            return Phase5RiskDecision(
                allowed=False,
                reason="no_averaging_down_short_block",
                details=details,
            )

    details["direction"] = "short"
    return Phase5RiskDecision(
        allowed=True,
        reason="no_avg_ok_short",
        details=details,
    )