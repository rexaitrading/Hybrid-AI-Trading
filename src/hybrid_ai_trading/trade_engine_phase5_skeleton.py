from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from hybrid_ai_trading.risk_manager_phase5_bridge import (
    RiskManagerPhase5,
    PositionSnapshot,
    AddRequest,
)


@dataclass
class AddDecision:
    symbol: str
    side: str
    can_add: bool
    reason: str
    unrealized_pnl_bp: float
    existing_notional: float
    additional_notional: float


class TradeEnginePhase5:
    """
    Minimal, offline-only trade engine skeleton that shows how Phase 5 risk
    is consulted before scaling into positions.

    This does NOT place orders and does NOT modify any live engine modules.
    """

    def __init__(self) -> None:
        self.risk_manager = RiskManagerPhase5()

    def consider_add(self, position: PositionSnapshot, add: AddRequest) -> AddDecision:
        can_add = self.risk_manager.can_add(position, add)

        if position.unrealized_pnl_bp <= 0.0:
            base_reason = "no_averaging_down_block"
        else:
            base_reason = "insufficient_cushion" if not can_add else "okay"

        return AddDecision(
            symbol=position.symbol,
            side=position.side,
            can_add=can_add,
            reason=base_reason,
            unrealized_pnl_bp=position.unrealized_pnl_bp,
            existing_notional=position.notional,
            additional_notional=add.additional_notional,
        )


def demo() -> None:
    """
    Offline demo to show how TradeEnginePhase5 would interact with RiskManagerPhase5.
    """
    engine = TradeEnginePhase5()

    # Example scenarios similar to the tests:
    pos_loser = PositionSnapshot(
        symbol="AAPL",
        side="LONG",
        unrealized_pnl_bp=-5.0,
        notional=10_000.0,
    )
    pos_small_win = PositionSnapshot(
        symbol="AAPL",
        side="LONG",
        unrealized_pnl_bp=2.0,
        notional=10_000.0,
    )
    pos_big_win = PositionSnapshot(
        symbol="AAPL",
        side="LONG",
        unrealized_pnl_bp=10.0,
        notional=10_000.0,
    )

    add_req = AddRequest(
        additional_notional=5_000.0,
        additional_shares_round_trip=100,
    )

    for label, pos in [
        ("LOSER", pos_loser),
        ("SMALL_WIN", pos_small_win),
        ("BIG_WIN", pos_big_win),
    ]:
        decision = engine.consider_add(pos, add_req)
        print(
            f"[TradeEnginePhase5] {label}: "
            f"symbol={decision.symbol} side={decision.side} "
            f"unrealized_pnl_bp={decision.unrealized_pnl_bp:.2f} "
            f"existing_notional={decision.existing_notional:.0f} "
            f"add_notional={decision.additional_notional:.0f} "
            f"-> can_add={decision.can_add} reason={decision.reason}"
        )


if __name__ == "__main__":
    demo()