from hybrid_ai_trading.risk.risk_phase5_no_avg import no_averaging_down_gate
from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision


def test_no_avg_allows_flat_position():
    decision = no_averaging_down_gate(
        side="BUY",
        qty=1.0,
        price=100.0,
        pos_qty=0.0,
        avg_price=0.0,
    )

    assert isinstance(decision, Phase5RiskDecision)
    assert decision.allowed is True
    assert "no_avg_ok_flat" in decision.reason


def test_no_avg_blocks_long_averaging_down():
    # Long 1 @ 100, trying to buy more at 95 → averaging down long.
    decision = no_averaging_down_gate(
        side="BUY",
        qty=1.0,
        price=95.0,
        pos_qty=1.0,
        avg_price=100.0,
    )

    assert isinstance(decision, Phase5RiskDecision)
    assert decision.allowed is False
    assert decision.reason == "no_averaging_down_long_block"


def test_no_avg_allows_long_at_better_or_equal_price():
    # Long 1 @ 100, buy more at 105 → not averaging down.
    decision = no_averaging_down_gate(
        side="BUY",
        qty=1.0,
        price=105.0,
        pos_qty=1.0,
        avg_price=100.0,
    )

    assert isinstance(decision, Phase5RiskDecision)
    assert decision.allowed is True
    assert decision.reason == "no_avg_ok_long"


def test_no_avg_blocks_short_averaging_down():
    # Short -1 @ 100, trying to short more at 105 → averaging down short.
    decision = no_averaging_down_gate(
        side="SELL",
        qty=1.0,
        price=105.0,
        pos_qty=-1.0,
        avg_price=100.0,
    )

    assert isinstance(decision, Phase5RiskDecision)
    assert decision.allowed is False
    assert decision.reason == "no_averaging_down_short_block"


def test_no_avg_allows_short_at_better_or_equal_price():
    # Short -1 @ 100, short more at 95 → not averaging down.
    decision = no_averaging_down_gate(
        side="SELL",
        qty=1.0,
        price=95.0,
        pos_qty=-1.0,
        avg_price=100.0,
    )

    assert isinstance(decision, Phase5RiskDecision)
    assert decision.allowed is True
    assert decision.reason == "no_avg_ok_short"