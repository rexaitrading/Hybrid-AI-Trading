from hybrid_ai_trading.risk.risk_phase5_account_caps import account_daily_loss_gate
from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision


def test_account_daily_loss_gate_blocks_when_below_cap():
    decision = account_daily_loss_gate(
        account_realized_pnl=-1200.0,
        account_daily_loss_cap=-1000.0,
    )

    assert isinstance(decision, Phase5RiskDecision)
    assert decision.allowed is False
    assert decision.reason == "account_daily_loss_cap_block"


def test_account_daily_loss_gate_allows_when_above_cap():
    decision = account_daily_loss_gate(
        account_realized_pnl=-500.0,
        account_daily_loss_cap=-1000.0,
    )

    assert isinstance(decision, Phase5RiskDecision)
    assert decision.allowed is True
    assert decision.reason == "account_daily_loss_ok"