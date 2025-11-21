"""
Phase 5: No-Averaging-Down policy helper.

This module is currently *not wired* into the main RiskManager.
It defines the data structures and helper logic for enforcing:

- no averaging down (no adding to losing positions)
- optional allowing of averaging up (pyramiding winners)
- cooldown after stop-out before re-entry

To activate this in the live system, RiskManager and TradeEngine
will later import and call these helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class AveragingDownPolicy:
    enabled: bool = True
    allow_averaging_up: bool = False
    max_adds_per_trade: int = 0
    cooldown_bars_after_stop: int = 10
    cooldown_seconds_after_stop: int = 600


@dataclass
class PositionState:
    qty: int = 0
    avg_entry_price: float = 0.0
    last_exit_ts: Optional[datetime] = None
    last_exit_reason: Optional[str] = None
    last_exit_pnl: Optional[float] = None
    bars_since_exit: int = 0

    def is_flat(self) -> bool:
        return self.qty == 0

    def is_long(self) -> bool:
        return self.qty > 0

    def is_short(self) -> bool:
        return self.qty < 0


class NoAveragingDownViolation(Exception):
    """Raised when a no-averaging-down rule is violated."""


class NoAveragingDownHelper:
    """
    Stateless helper that checks orders against the no-averaging-down policy.

    This class assumes an order object with fields:
    - side: "LONG" or "SHORT"
    - qty: positive integer quantity
    - price: float
    """

    def validate_order(
        self,
        *,
        side: str,
        qty: int,
        price: float,
        position: PositionState,
        policy: AveragingDownPolicy,
    ) -> None:
        """
        Validate a proposed order against the no-averaging-down rules.

        Raises NoAveragingDownViolation if the order is not allowed.
        """
        if not policy.enabled:
            return

        # Normalize side
        side = side.upper()

        # Fresh entry: enforce cooldown after a stop-out, then allow.
        if position.is_flat():
            self._enforce_cooldown_after_stop(position, policy)
            return

        # Compute proposed new quantity with signed math
        signed_qty = qty if side == "LONG" else -qty
        new_qty = position.qty + signed_qty

        # If new absolute qty is smaller -> scaling out / closing -> always allowed.
        if abs(new_qty) < abs(position.qty):
            return

        # At this point, we are adding size in the same direction.
        # Figure out whether this is averaging down or up.
        avg_entry = position.avg_entry_price
        px = price

        if position.is_long():
            # Long: averaging down means buying at a lower price than average.
            if px < avg_entry:
                raise NoAveragingDownViolation(
                    f"Attempt to add to a long below avg entry "
                    f"(price={px:.4f} < avg_entry={avg_entry:.4f})"
                )
            if not policy.allow_averaging_up:
                raise NoAveragingDownViolation(
                    "Adding to a winning long is disabled by policy."
                )
        elif position.is_short():
            # Short: averaging down means shorting at a higher price than average.
            if px > avg_entry:
                raise NoAveragingDownViolation(
                    f"Attempt to add to a short above avg entry "
                    f"(price={px:.4f} > avg_entry={avg_entry:.4f})"
                )
            if not policy.allow_averaging_up:
                raise NoAveragingDownViolation(
                    "Adding to a winning short is disabled by policy."
                )

        # Optional: if max_adds_per_trade is used, the caller can track
        # a separate "adds_used" counter and enforce it before calling here.

    def _enforce_cooldown_after_stop(
        self,
        position: PositionState,
        policy: AveragingDownPolicy,
    ) -> None:
        """
        Enforce cooldown after a stop-out before allowing a fresh entry.

        This helper assumes the caller updates PositionState.bars_since_exit
        on each new bar, and sets last_exit_reason / last_exit_pnl when
        positions are closed.
        """
        if position.last_exit_reason != "STOP":
            return

        if position.last_exit_pnl is None or position.last_exit_pnl >= 0:
            return

        # Bars-based cooldown
        if position.bars_since_exit < policy.cooldown_bars_after_stop:
            remaining = policy.cooldown_bars_after_stop - position.bars_since_exit
            raise NoAveragingDownViolation(
                f"Cooldown after stop-out: wait {remaining} more bar(s) "
                f"before opening a new position."
            )

        # Time-based cooldown can be added here if desired; for now the
        # bars-based rule is the primary control.