from types import SimpleNamespace

from hybrid_ai_trading.risk.risk_manager import RiskManager
from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision


def make_rm_with_simple_state():
    rm = RiskManager()
    # Simple config object with daily loss cap
    rm.config = SimpleNamespace(phase5_daily_loss_cap=-500.0)
    rm.daily_pnl = {}
    rm.positions = {}
    return rm


def test_combined_gate_blocks_on_daily_loss_when_exposure_increases():
    rm = make_rm_with_simple_state()
    rm.daily_pnl["2025-11-10"] = -600.0  # below cap
    rm.positions["SPY"] = SimpleNamespace(qty=1.0, avg_price=100.0)

    trade = {
        "symbol": "SPY",
        "side": "BUY",
        "qty": 1.0,
        "price": 101.0,
        "regime": "SPY_ORB_LIVE",
        "day_id": "2025-11-10",
    }

    decision = rm.check_trade_phase5(trade)

    assert isinstance(decision, Phase5RiskDecision)
    assert decision.allowed is False
    assert decision.reason == "daily_loss_cap_block"


def test_combined_gate_blocks_on_no_averaging_down_when_daily_loss_ok():
    rm = make_rm_with_simple_state()
    rm.daily_pnl["2025-11-10"] = -100.0  # above cap, so daily loss gate passes
    rm.positions["SPY"] = SimpleNamespace(qty=1.0, avg_price=100.0)

    # Long 1 @100, trying to buy more at 95 -> averaging down long
    trade = {
        "symbol": "SPY",
        "side": "BUY",
        "qty": 1.0,
        "price": 95.0,
        "regime": "SPY_ORB_LIVE",
        "day_id": "2025-11-10",
    }

    decision = rm.check_trade_phase5(trade)

    assert isinstance(decision, Phase5RiskDecision)
    assert decision.allowed is False
    assert decision.reason == "no_averaging_down_long_block"