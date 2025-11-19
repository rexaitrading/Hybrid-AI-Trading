from hybrid_ai_trading.trade_engine_phase5_skeleton import (
    TradeEnginePhase5,
    AddDecision,
)
from hybrid_ai_trading.risk_manager_phase5_bridge import (
    PositionSnapshot,
    AddRequest,
)
from hybrid_ai_trading.risk_no_averaging_down import RiskConfig, CostConfig


def _make_engine() -> TradeEnginePhase5:
    engine = TradeEnginePhase5()
    # Override configs to make tests stable and independent of env/policy.
    engine.risk_manager.risk_cfg = RiskConfig(no_averaging_down=True, min_add_cushion_bp=3.0)
    engine.risk_manager.cost_cfg = CostConfig(slippage_bp=1.0, fee_bp=0.3, fee_per_share=0.004)
    return engine


def test_engine_blocks_add_for_losing_position() -> None:
    engine = _make_engine()
    pos = PositionSnapshot(
        symbol="AAPL",
        side="LONG",
        unrealized_pnl_bp=-5.0,
        notional=10_000.0,
    )
    add = AddRequest(
        additional_notional=5_000.0,
        additional_shares_round_trip=100,
    )

    decision: AddDecision = engine.consider_add(pos, add)
    assert decision.can_add is False
    assert decision.reason == "no_averaging_down_block"


def test_engine_blocks_add_for_small_win_below_cushion() -> None:
    engine = _make_engine()
    pos = PositionSnapshot(
        symbol="AAPL",
        side="LONG",
        unrealized_pnl_bp=2.0,
        notional=10_000.0,
    )
    add = AddRequest(
        additional_notional=5_000.0,
        additional_shares_round_trip=100,
    )

    decision: AddDecision = engine.consider_add(pos, add)
    assert decision.can_add is False
    assert decision.reason == "insufficient_cushion"


def test_engine_allows_add_for_strong_win_above_cushion() -> None:
    engine = _make_engine()
    pos = PositionSnapshot(
        symbol="AAPL",
        side="LONG",
        unrealized_pnl_bp=10.0,
        notional=10_000.0,
    )
    add = AddRequest(
        additional_notional=5_000.0,
        additional_shares_round_trip=100,
    )

    decision: AddDecision = engine.consider_add(pos, add)
    assert decision.can_add is True
    assert decision.reason == "okay"