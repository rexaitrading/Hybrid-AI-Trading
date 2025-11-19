from hybrid_ai_trading.risk_manager_phase5_bridge import (
    RiskManagerPhase5,
    PositionSnapshot,
    AddRequest,
)
from hybrid_ai_trading.risk_no_averaging_down import RiskConfig, CostConfig


def _make_rm() -> RiskManagerPhase5:
    rm = RiskManagerPhase5()
    # Override configs explicitly so tests are stable and independent of env/policy file.
    rm.risk_cfg = RiskConfig(no_averaging_down=True, min_add_cushion_bp=3.0)
    rm.cost_cfg = CostConfig(slippage_bp=1.0, fee_bp=0.3, fee_per_share=0.004)
    return rm


def test_phase5_bridge_blocks_losing_position() -> None:
    rm = _make_rm()

    pos = PositionSnapshot(
        symbol="AAPL",
        side="LONG",
        unrealized_pnl_bp=-5.0,
        notional=10_000.0,
    )
    add_req = AddRequest(
        additional_notional=5_000.0,
        additional_shares_round_trip=100,
    )

    assert rm.can_add(pos, add_req) is False


def test_phase5_bridge_blocks_small_win_below_cushion() -> None:
    rm = _make_rm()

    pos = PositionSnapshot(
        symbol="AAPL",
        side="LONG",
        unrealized_pnl_bp=2.0,  # small winner
        notional=10_000.0,
    )
    add_req = AddRequest(
        additional_notional=5_000.0,
        additional_shares_round_trip=100,
    )

    allowed = rm.can_add(pos, add_req)
    assert allowed is False


def test_phase5_bridge_allows_strong_win_above_cost_plus_cushion() -> None:
    rm = _make_rm()

    pos = PositionSnapshot(
        symbol="AAPL",
        side="LONG",
        unrealized_pnl_bp=10.0,  # strong winner
        notional=10_000.0,
    )
    add_req = AddRequest(
        additional_notional=5_000.0,
        additional_shares_round_trip=100,
    )

    allowed = rm.can_add(pos, add_req)
    assert allowed is True


def test_phase5_bridge_blocks_unknown_side() -> None:
    rm = _make_rm()

    pos = PositionSnapshot(
        symbol="AAPL",
        side="FLAT",  # unknown side
        unrealized_pnl_bp=10.0,
        notional=10_000.0,
    )
    add_req = AddRequest(
        additional_notional=5_000.0,
        additional_shares_round_trip=100,
    )

    allowed = rm.can_add(pos, add_req)
    assert allowed is False