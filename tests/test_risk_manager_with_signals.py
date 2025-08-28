import pytest
from src.risk.risk_manager import RiskManager


def test_signal_passes_when_safe():
    rm = RiskManager()
    rm.daily_pnl = 0.0
    assert rm.control_signal("BUY") == "BUY"
    assert rm.control_signal("SELL") == "SELL"


def test_signal_blocked_when_daily_limit_hit():
    rm = RiskManager(daily_loss_limit=-0.03)
    rm.daily_pnl = -0.05  # already below limit
    assert rm.control_signal("BUY") == "HOLD"
    assert rm.control_signal("SELL") == "HOLD"


def test_hold_signal_always_passes():
    rm = RiskManager(daily_loss_limit=-0.03)
    rm.daily_pnl = -0.10
    assert rm.control_signal("HOLD") == "HOLD"


def test_check_trade_allows_profit():
    rm = RiskManager()
    assert rm.check_trade(0.02)  # +2%
    assert rm.daily_pnl > 0


def test_check_trade_blocks_big_loss():
    rm = RiskManager(trade_loss_limit=-0.01)
    assert not rm.check_trade(-0.05)  # -5% is too much


def test_check_trade_blocks_if_daily_loss_breached():
    rm = RiskManager(daily_loss_limit=-0.03)
    rm.daily_pnl = -0.02
    assert not rm.check_trade(-0.02)  # would breach daily cap
