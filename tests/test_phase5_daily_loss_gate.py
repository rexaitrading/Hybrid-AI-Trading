from hybrid_ai_trading.risk.risk_phase5_daily_loss import daily_loss_gate
from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision


def test_daily_loss_gate_blocks_when_exposure_increases_and_below_cap():
    decision = daily_loss_gate(
        realized_pnl=-600.0,
        daily_loss_cap=-500.0,
        pos_qty=1.0,
        new_pos_qty=2.0,
    )

    assert isinstance(decision, Phase5RiskDecision)
    assert decision.allowed is False
    assert decision.reason == "daily_loss_cap_block"
    assert decision.details["increasing_exposure"] is True


def test_daily_loss_gate_allows_exposure_increase_when_above_cap():
    decision = daily_loss_gate(
        realized_pnl=-200.0,
        daily_loss_cap=-500.0,
        pos_qty=1.0,
        new_pos_qty=2.0,
    )

    assert isinstance(decision, Phase5RiskDecision)
    assert decision.allowed is True
    assert decision.reason == "daily_loss_ok"
    assert decision.details["increasing_exposure"] is True


def test_daily_loss_gate_allows_reduce_or_flat_even_if_below_cap():
    decision = daily_loss_gate(
        realized_pnl=-600.0,
        daily_loss_cap=-500.0,
        pos_qty=2.0,
        new_pos_qty=1.0,
    )

    assert isinstance(decision, Phase5RiskDecision)
    assert decision.allowed is True
    assert decision.reason == "daily_loss_ok_reduce_or_flat"
    assert decision.details["increasing_exposure"] is False