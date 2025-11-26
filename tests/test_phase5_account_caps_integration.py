from types import SimpleNamespace

from hybrid_ai_trading.risk.risk_manager import RiskManager
from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision


def make_rm_with_account_caps(realized_pnl: float, cap: float) -> RiskManager:
    """
    Helper for tests:

    - account_realized_pnl: account-wide realized PnL
    - phase5_account_daily_loss_cap: account-wide cap
    - phase5_daily_loss_cap + daily_pnl: symbol-level daily loss state
    """
    rm = RiskManager()
    rm.config = SimpleNamespace(
        phase5_account_daily_loss_cap=cap,
        phase5_daily_loss_cap=cap,  # use same cap for symbol-level in tests
    )
    rm.account_realized_pnl = realized_pnl
    # Symbol-level daily PnL for the given day_id
    rm.daily_pnl = {"2025-11-10": realized_pnl}
    rm.positions = {}
    return rm


def test_account_cap_blocks_when_below_cap():
    rm = make_rm_with_account_caps(realized_pnl=-1500.0, cap=-1000.0)
    decision = rm.check_trade_phase5(
        {
            "symbol": "SPY",
            "side": "BUY",
            "qty": 1.0,
            "price": 500.0,
            "regime": "SPY_ORB_LIVE",
            "day_id": "2025-11-10",
        }
    )

    assert isinstance(decision, Phase5RiskDecision)
    assert decision.allowed is False
    assert decision.reason == "account_daily_loss_cap_block"


def test_account_cap_allows_when_above_cap_and_symbol_gates_ok():
    rm = make_rm_with_account_caps(realized_pnl=-300.0, cap=-1000.0)
    decision = rm.check_trade_phase5(
        {
            "symbol": "SPY",
            "side": "BUY",
            "qty": 1.0,
            "price": 500.0,
            "regime": "SPY_ORB_LIVE",
            "day_id": "2025-11-10",
        }
    )

    assert isinstance(decision, Phase5RiskDecision)
    assert decision.allowed is True
    assert decision.reason == "phase5_risk_ok"