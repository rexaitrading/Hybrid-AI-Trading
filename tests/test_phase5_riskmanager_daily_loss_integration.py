from hybrid_ai_trading.risk.risk_manager import RiskManager
from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision


def test_riskmanager_has_check_trade_phase5_method():
    rm = RiskManager()
    assert hasattr(rm, "check_trade_phase5")


def test_riskmanager_check_trade_phase5_returns_phase5_riskdecision():
    rm = RiskManager()

    trade = {
        "symbol": "SPY",
        "side": "BUY",
        "qty": 1.0,
        "price": 500.0,
        "regime": "SPY_ORB_LIVE",
        "day_id": "2025-11-10",
    }

    decision = rm.check_trade_phase5(trade)

    assert isinstance(decision, Phase5RiskDecision)
    assert decision.allowed is True
    # With new_pos_qty == pos_qty, the helper behaves as a non-blocking stub.
    assert "daily_loss" in decision.reason