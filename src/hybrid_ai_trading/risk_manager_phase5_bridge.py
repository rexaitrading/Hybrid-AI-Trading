from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from hybrid_ai_trading.risk_no_averaging_down import (
    CostConfig,
    RiskConfig,
    can_add_to_position,
    load_cost_config_from_env,
    load_risk_config_from_env_and_policy,
)


@dataclass
class PositionSnapshot:
    symbol: str
    side: str  # "LONG" or "SHORT"
    unrealized_pnl_bp: float
    notional: float


@dataclass
class AddRequest:
    additional_notional: float
    additional_shares_round_trip: int


class RiskManagerPhase5:
    """
    Thin bridge showing how a future RiskManager would call the Phase 5 gate.

    This class is intentionally standalone and does not modify existing
    risk_manager.py or trade_engine modules.
    """

    def __init__(
        self,
        policy_path: str = "config/risk_phase5_no_averaging_down.json",
    ) -> None:
        self.policy_path = policy_path
        self.risk_cfg: RiskConfig = load_risk_config_from_env_and_policy(policy_path=policy_path)
        self.cost_cfg: CostConfig = load_cost_config_from_env()

    def reload_from_env(self) -> None:
        """
        Optional helper: refresh configs from env + policy file.
        Useful if you change env vars between runs.
        """
        self.risk_cfg = load_risk_config_from_env_and_policy(policy_path=self.policy_path)
        self.cost_cfg = load_cost_config_from_env()

    def can_add(self, position: PositionSnapshot, add: AddRequest) -> bool:
        """
        Decide whether we may increase position size under Phase 5 rules.

        In a future integration, trade_engine would call this BEFORE
        sending an add-to-position order.
        """
        return can_add_to_position(
            side=position.side,
            position_unrealized_pnl_bp=position.unrealized_pnl_bp,
            existing_notional=position.notional,
            additional_notional=add.additional_notional,
            additional_shares_round_trip=add.additional_shares_round_trip,
            risk_cfg=self.risk_cfg,
            cost_cfg=self.cost_cfg,
        )


def demo() -> None:
    """
    Small demo that shows how the bridge would behave, using current env vars.
    """
    rm = RiskManagerPhase5()

    pos_loser = PositionSnapshot(
        symbol="AAPL",
        side="LONG",
        unrealized_pnl_bp=-5.0,
        notional=10_000.0,
    )
    add_req = AddRequest(
        additional_notional=5_000.0,
        additional_shares_round_trip=100,
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

    print("[Phase5Bridge] risk_cfg:", rm.risk_cfg)
    print("[Phase5Bridge] cost_cfg:", rm.cost_cfg)

    print("[Phase5Bridge] LOSER can_add:", rm.can_add(pos_loser, add_req))
    print("[Phase5Bridge] SMALL WIN can_add:", rm.can_add(pos_small_win, add_req))
    print("[Phase5Bridge] BIG WIN can_add:", rm.can_add(pos_big_win, add_req))


if __name__ == "__main__":
    demo()