"""
Micro-Tests: RiskManager (Hybrid AI Quant Pro v24.7 – Hedge-Fund OE Grade, AAA+ Coverage)
========================================================================================
Forces 100% coverage of risk_manager.py:
- Legacy kwargs (max_daily_loss, max_position_risk)
- Approve trade (valid + invalid size)
- Update equity (normal + drawdown breach)
- Trade loss guard
- Daily loss guard (normal + breach)
- Exposure & leverage guards
- Portfolio error branch
- DB logger (success + error)
- Kelly sizing (normal + invalid + regime scaling + exception)
- Control signal override (force HOLD)
- Reset day (success + error branch)
"""

import pytest
import logging
from hybrid_ai_trading.risk.risk_manager import RiskManager


# ----------------------------------------------------------------------
# Legacy kwargs
# ----------------------------------------------------------------------
def test_legacy_kwargs_force_lines():
    rm = RiskManager(max_daily_loss=-0.05, max_position_risk=-0.02)
    assert rm.daily_loss_limit == -0.05
    assert rm.trade_loss_limit == -0.02


# ----------------------------------------------------------------------
# Approve trade
# ----------------------------------------------------------------------
def test_approve_trade_paths(caplog):
    rm = RiskManager()
    caplog.set_level(logging.WARNING)
    assert rm.approve_trade("AAPL", "BUY", 10) is True
    assert rm.approve_trade("AAPL", "BUY", 0) is False
    assert "non-positive size" in caplog.text.lower()


# ----------------------------------------------------------------------
# Update equity
# ----------------------------------------------------------------------
def test_update_equity_normal_and_breach(caplog):
    rm = RiskManager(equity=100, max_drawdown=0.5)
    assert rm.update_equity(10) is True
    caplog.set_level(logging.CRITICAL)
    rm.equity = 40
    assert rm.update_equity(-20) is False
    assert "drawdown" in caplog.text.lower()


# ----------------------------------------------------------------------
# Trade & daily loss guards
# ----------------------------------------------------------------------
def test_trade_and_daily_loss_guards(caplog):
    rm = RiskManager(trade_loss_limit=-0.01)
    caplog.set_level(logging.WARNING)
    assert rm.check_trade("AAPL", "BUY", 1, -0.02) is False
    assert "trade_loss" in caplog.text.lower()

    rm = RiskManager(daily_loss_limit=-0.01, trade_loss_limit=None)
    rm.daily_pnl = -0.02
    caplog.clear()
    assert rm.check_trade("AAPL", "BUY", 1, -0.005) is False
    assert "daily_loss" in caplog.text.lower()


# ----------------------------------------------------------------------
# Exposure & leverage guards
# ----------------------------------------------------------------------
class HighRiskPortfolio:
    def get_leverage(self): return 10
    def get_total_exposure(self): return 9999

def test_exposure_and_leverage_guards(caplog):
    rm = RiskManager(max_leverage=2, max_portfolio_exposure=0.1,
                     portfolio=HighRiskPortfolio(), equity=1000)
    caplog.set_level(logging.WARNING)
    assert rm.check_trade("AAPL", "BUY", 1, 1) is False
    assert "leverage" in caplog.text.lower() or "exposure" in caplog.text.lower()


# ----------------------------------------------------------------------
# Portfolio error branch
# ----------------------------------------------------------------------
class BadPortfolio:
    def get_leverage(self): raise Exception("lev fail")
    def get_total_exposure(self): return 1000

def test_portfolio_error_branch(caplog):
    rm = RiskManager(portfolio=BadPortfolio())
    caplog.set_level(logging.ERROR)
    assert rm.check_trade("AAPL", "BUY", 1, 1) is False
    assert "portfolio" in caplog.text.lower()


# ----------------------------------------------------------------------
# DB logger branches
# ----------------------------------------------------------------------
class GoodLogger:
    def __init__(self): self.logged = []
    def log(self, data): self.logged.append(data)

class BadLogger:
    def log(self, data): raise Exception("db fail")

def test_db_logger_success_and_error(caplog):
    good = GoodLogger()
    rm = RiskManager(db_logger=good)
    res = rm.check_trade("AAPL", "BUY", 1, 5)
    assert res is True
    assert good.logged and good.logged[0]["symbol"] == "AAPL"

    caplog.set_level(logging.ERROR)
    rm = RiskManager(db_logger=BadLogger())
    res2 = rm.check_trade("AAPL", "BUY", 1, 5)
    assert res2 is True
    assert "db log failed" in caplog.text.lower()


# ----------------------------------------------------------------------
# Kelly sizing
# ----------------------------------------------------------------------
def test_kelly_size_normal_invalid_and_exception(caplog):
    rm = RiskManager()
    # Normal case
    f = rm.kelly_size(0.6, 2)
    assert 0.0 <= f <= 1.0

    # With regime scaling
    f_reg = rm.kelly_size(0.6, 2, regime=0.5)
    assert 0.0 <= f_reg <= f

    # Invalid inputs
    assert rm.kelly_size(0, 1) == 0.0
    assert rm.kelly_size(1, 1) == 0.0
    assert rm.kelly_size(0.5, 0) == 0.0

    # Exception path
    class Exploder:
        def __rtruediv__(self, other): raise Exception("boom")
    caplog.set_level(logging.ERROR)
    assert rm.kelly_size(0.6, Exploder()) == 0.0
    assert "kelly sizing failed" in caplog.text.lower()


# ----------------------------------------------------------------------
# Control signal
# ----------------------------------------------------------------------
def test_control_signal_override(caplog):
    rm = RiskManager(daily_loss_limit=-0.01)
    rm.daily_pnl = -0.02
    caplog.set_level(logging.WARNING)
    sig = rm.control_signal("buy")
    assert sig == "HOLD"
    assert "override" in caplog.text.lower()


# ----------------------------------------------------------------------
# Reset day
# ----------------------------------------------------------------------
def test_reset_day_success_and_error(caplog):
    rm = RiskManager()
    out = rm.reset_day()
    assert out["status"] == "ok"

    class BadPortfolio:
        def reset_day(self): raise Exception("boom")
    rm.portfolio = BadPortfolio()
    caplog.set_level(logging.ERROR)
    out = rm.reset_day()
    assert out["status"] == "error"
    assert "boom" in out["reason"]
