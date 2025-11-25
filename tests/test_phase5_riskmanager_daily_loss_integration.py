from types import SimpleNamespace

from hybrid_ai_trading.risk.risk_manager import RiskManager
from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision


def make_rm_with_safe_state():
    rm = RiskManager()
    # Configure a daily loss cap that is BELOW current realized PnL
    # so the daily loss gate passes for this test.
    rm.config = SimpleNamespace(phase5_daily_loss_cap=-500.0)
    rm.daily_pnl = {"2025-11-10": -100.0}  # above cap, so allowed
    rm.positions = {}
    return rm


def test_riskmanager_has_check_trade_phase5_method():
    rm = make_rm_with_safe_state()
    assert hasattr(rm, "check_trade_phase5")


def test_riskmanager_check_trade_phase5_returns_phase5_riskdecision():
    rm = make_rm_with_safe_state()

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
    # With daily loss OK and no position, no-avg gate also passes.
    assert decision.allowed is True
    assert decision.reason == "phase5_risk_ok"