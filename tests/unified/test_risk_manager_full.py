"""
Unit Tests: RiskManager (Hybrid AI Quant Pro v24.8 – Hedge-Fund OE Grade, 100% Coverage)
========================================================================================
Covers ALL paths in risk_manager.py:
- Initialization (defaults, legacy kwargs)
- approve_trade (valid, invalid size)
- update_equity (normal, breach)
- check_trade:
    • Per-trade loss guard
    • Daily loss guard
    • Portfolio leverage & exposure guard
    • Portfolio exception branch
    • DB logger success + failure
- kelly_size:
    • Normal case
    • Invalid inputs
    • Regime scaling
    • Exception branch
- control_signal (HOLD pass-through, override on breach, casing normalization)
- reset_day:
    • With portfolio success
    • Without portfolio
    • Failure path
"""

import logging

import pytest

from hybrid_ai_trading.risk.risk_manager import RiskManager


# ----------------------------------------------------------------------
# Dummy helpers
# ----------------------------------------------------------------------
class DummyPortfolio:
    def __init__(
        self,
        lev=1.0,
        exp=1000,
        fail_leverage=False,
        fail_exposure=False,
        fail_reset=False,
    ):
        self._lev = lev
        self._exp = exp
        self.fail_leverage = fail_leverage
        self.fail_exposure = fail_exposure
        self.fail_reset = fail_reset
        self.reset_called = False

    def get_leverage(self):
        if self.fail_leverage:
            raise Exception("lev fail")
        return self._lev

    def get_total_exposure(self):
        if self.fail_exposure:
            raise Exception("exp fail")
        return self._exp

    def reset_day(self):
        if self.fail_reset:
            raise Exception("reset fail")
        self.reset_called = True


class DummyLogger:
    def __init__(self, should_fail=False):
        self.logged = []
        self.should_fail = should_fail

    def log(self, record):
        if self.should_fail:
            raise Exception("db fail")
        self.logged.append(record)


# ----------------------------------------------------------------------
# Init / legacy kwargs
# ----------------------------------------------------------------------
def test_init_defaults_and_legacy_kwargs():
    rm1 = RiskManager()
    assert rm1.starting_equity == 100000.0

    rm2 = RiskManager(max_daily_loss=-0.05, max_position_risk=-0.02)
    assert rm2.daily_loss_limit == -0.05
    assert rm2.trade_loss_limit == -0.02


# ----------------------------------------------------------------------
# approve_trade
# ----------------------------------------------------------------------
def test_approve_trade_paths(caplog):
    rm = RiskManager()
    caplog.set_level(logging.WARNING)
    assert not rm.approve_trade("AAPL", "BUY", 0)
    assert "non-positive" in caplog.text
    assert rm.approve_trade("AAPL", "BUY", 10)


# ----------------------------------------------------------------------
# update_equity
# ----------------------------------------------------------------------
def test_update_equity_paths(caplog):
    rm = RiskManager(equity=100, max_drawdown=0.1)
    assert rm.update_equity(5)
    caplog.set_level(logging.CRITICAL)
    assert not rm.update_equity(-100)  # breach
    assert "drawdown" in caplog.text


# ----------------------------------------------------------------------
# check_trade: per-trade + daily loss
# ----------------------------------------------------------------------
def test_check_trade_loss_branches(caplog):
    rm = RiskManager(trade_loss_limit=-0.01, daily_loss_limit=-0.02)

    # Per-trade loss breach
    caplog.set_level(logging.WARNING)
    assert not rm.check_trade("AAPL", "BUY", 1, -0.02)
    assert "trade_loss" in caplog.text

    # Daily loss breach
    rm2 = RiskManager(daily_loss_limit=-0.01)
    rm2.daily_pnl = -0.02
    caplog.set_level(logging.WARNING)
    assert not rm2.check_trade("AAPL", "BUY", 1, 0.0)
    assert "daily_loss" in caplog.text


# ----------------------------------------------------------------------
# check_trade: portfolio & db_logger
# ----------------------------------------------------------------------
def test_check_trade_with_portfolio_and_db_logger(caplog):
    # Leverage breach
    p = DummyPortfolio(lev=10, exp=1000)
    rm = RiskManager(portfolio=p, max_leverage=5, equity=100000)
    caplog.set_level(logging.WARNING)
    assert not rm.check_trade("AAPL", "BUY", 1, 1000)
    assert "leverage" in caplog.text

    # Exposure breach
    p2 = DummyPortfolio(lev=1, exp=60000)
    rm2 = RiskManager(portfolio=p2, max_portfolio_exposure=0.3, equity=100000)
    caplog.set_level(logging.WARNING)
    assert not rm2.check_trade("AAPL", "BUY", 1, 1000)
    assert "exposure" in caplog.text

    # Portfolio error
    pfail = DummyPortfolio(fail_leverage=True)
    rm3 = RiskManager(portfolio=pfail)
    caplog.set_level(logging.ERROR)
    assert not rm3.check_trade("AAPL", "BUY", 1, 1000)
    assert "Portfolio check failed" in caplog.text or "portfolio" in caplog.text

    # DB logger success + failure
    good = DummyLogger()
    rm4 = RiskManager(db_logger=good)
    assert rm4.check_trade("AAPL", "BUY", 1, 10)
    assert good.logged

    bad = DummyLogger(should_fail=True)
    rm5 = RiskManager(db_logger=bad)
    caplog.set_level(logging.ERROR)
    rm5.check_trade("AAPL", "BUY", 1, 10)
    assert "DB log failed" in caplog.text


# ----------------------------------------------------------------------
# kelly_size
# ----------------------------------------------------------------------
def test_kelly_size_variants_and_exceptions(caplog):
    rm = RiskManager()
    # Normal + regime scaling
    f = rm.kelly_size(0.6, 2.0)
    assert 0.0 <= f <= 1.0
    f_reg = rm.kelly_size(0.6, 2.0, regime=0.5)
    assert 0.0 <= f_reg <= f

    # Invalid inputs
    assert rm.kelly_size(-1, 2.0) == 0.0
    assert rm.kelly_size(0.6, 0.0) == 0.0
    assert rm.kelly_size(2.0, 2.0) == 0.0

    # Exception path
    class Exploder:
        def __rtruediv__(self, other):
            raise Exception("boom")

    caplog.set_level(logging.ERROR)
    assert rm.kelly_size(0.6, Exploder()) == 0.0
    assert "Kelly sizing failed" in caplog.text or "kelly" in caplog.text


# ----------------------------------------------------------------------
# control_signal
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "signal,pnl,expected",
    [("HOLD", 0.0, "HOLD"), ("BUY", -999, "HOLD"), ("sell", 0.0, "SELL")],
)
def test_control_signal_variants(signal, pnl, expected, caplog):
    rm = RiskManager(daily_loss_limit=-0.01)
    rm.daily_pnl = pnl
    caplog.set_level(logging.WARNING)
    assert rm.control_signal(signal) == expected


# ----------------------------------------------------------------------
# reset_day
# ----------------------------------------------------------------------
def test_reset_day_with_and_without_portfolio(caplog):
    # Success with portfolio
    p = DummyPortfolio()
    rm = RiskManager(portfolio=p)
    caplog.set_level(logging.INFO)
    out = rm.reset_day()
    assert out["status"] == "ok"
    assert p.reset_called
    assert "Daily reset complete" in caplog.text

    # Without portfolio
    rm2 = RiskManager(portfolio=object())
    out2 = rm2.reset_day()
    assert out2["status"] == "ok"
    assert rm2.daily_pnl == 0.0

    # Failure branch
    pfail = DummyPortfolio(fail_reset=True)
    rm3 = RiskManager(portfolio=pfail)
    caplog.set_level(logging.ERROR)
    out3 = rm3.reset_day()
    assert out3["status"] == "error"
    assert "Reset day failed" in caplog.text or "fail" in out3["reason"]


"""
Extra Micro Tests: RiskManager guardrails & exception branches
Ensures 100% coverage of risk_manager.py
"""

import pytest


def test_daily_loss_guard_branch(caplog):
    rm = RiskManager(daily_loss_limit=-0.01)
    rm.daily_pnl = -0.02
    caplog.set_level(logging.WARNING)
    res = rm.check_trade("AAPL", "BUY", 1, 0.0)
    assert res is False
    assert "daily_loss" in caplog.text


def test_roi_guard_branch(caplog):
    rm = RiskManager(roi_min=0.05)
    rm.roi = 0.01
    caplog.set_level(logging.WARNING)
    res = rm.check_trade("AAPL", "BUY", 1, 0.0)
    assert res is False
    assert "ROI breach" in caplog.text


def test_sharpe_guard_breach(caplog):
    class BadSharpe(RiskManager):
        def sharpe_ratio(self):
            return 0.2

    rm = BadSharpe(sharpe_min=0.5)
    caplog.set_level(logging.WARNING)
    assert not rm.check_trade("AAPL", "BUY", 1, 1)
    assert "Sharpe breach" in caplog.text


def test_sharpe_guard_exception(caplog):
    class Exploder(RiskManager):
        def sharpe_ratio(self):
            raise Exception("bad sharpe")

    rm = Exploder(sharpe_min=1.0)
    caplog.set_level(logging.ERROR)
    assert not rm.check_trade("AAPL", "BUY", 1, 1)
    assert "Sharpe ratio check failed" in caplog.text


def test_sortino_guard_breach(caplog):
    class BadSortino(RiskManager):
        def sortino_ratio(self):
            return 0.1

    rm = BadSortino(sortino_min=0.5)
    caplog.set_level(logging.WARNING)
    assert not rm.check_trade("AAPL", "BUY", 1, 1)
    assert "Sortino breach" in caplog.text


def test_sortino_guard_exception(caplog):
    class Exploder(RiskManager):
        def sortino_ratio(self):
            raise Exception("bad sortino")

    rm = Exploder(sortino_min=1.0)
    caplog.set_level(logging.ERROR)
    assert not rm.check_trade("AAPL", "BUY", 1, 1)
    assert "Sortino ratio check failed" in caplog.text


def test_reset_day_exception_branch(caplog):
    class BadPortfolio:
        def reset_day(self):
            raise RuntimeError("boom")

    rm = RiskManager(portfolio=BadPortfolio())
    caplog.set_level(logging.ERROR)
    out = rm.reset_day()
    assert out["status"] == "error"
    assert "boom" in out["reason"]


def test_sharpe_ratio_breach(caplog):
    class BadSharpe(RiskManager):
        def sharpe_ratio(self):
            return 0.1

    rm = BadSharpe(sharpe_min=1.0)
    caplog.set_level("WARNING")
    assert not rm.check_trade("AAPL", "BUY", 1, 10)
    assert "Sharpe breach" in caplog.text


def test_sortino_ratio_breach(caplog):
    class BadSortino(RiskManager):
        def sortino_ratio(self):
            return 0.1

    rm = BadSortino(sortino_min=1.0)
    caplog.set_level("WARNING")
    assert not rm.check_trade("AAPL", "BUY", 1, 10)
    assert "Sortino breach" in caplog.text


def test_sharpe_and_sortino_exceptions(caplog):
    class BothFail(RiskManager):
        def sharpe_ratio(self):
            raise Exception("boom sharpe")

        def sortino_ratio(self):
            raise Exception("boom sortino")

    rm = BothFail(sharpe_min=1.0, sortino_min=1.0)
    caplog.set_level("ERROR")
    assert not rm.check_trade("AAPL", "BUY", 1, 10)
    assert "Sharpe ratio check failed" in caplog.text
    assert "Sortino ratio check failed" in caplog.text


def test_db_logger_failure(caplog):
    class BadLogger:
        def log(self, record):
            raise Exception("db fail")

    rm = RiskManager(db_logger=BadLogger())
    caplog.set_level("ERROR")
    assert rm.check_trade("AAPL", "BUY", 1, 10) is True
    assert "DB log failed" in caplog.text


def test_sharpe_ratio_breach_branch(caplog):
    class BadSharpe(RiskManager):
        def sharpe_ratio(self):
            return 0.1

    rm = BadSharpe(sharpe_min=1.0)
    caplog.set_level("WARNING")
    assert not rm.check_trade("AAPL", "BUY", 1, 10)
    assert "Sharpe breach" in caplog.text


def test_sortino_ratio_breach_branch(caplog):
    class BadSortino(RiskManager):
        def sortino_ratio(self):
            return 0.1

    rm = BadSortino(sortino_min=1.0)
    caplog.set_level("WARNING")
    assert not rm.check_trade("AAPL", "BUY", 1, 10)
    assert "Sortino breach" in caplog.text


def test_sharpe_ratio_exception_branch(caplog):
    class Exploder(RiskManager):
        def sharpe_ratio(self):
            raise Exception("boom sharpe")

    rm = Exploder(sharpe_min=1.0)
    caplog.set_level("ERROR")
    assert not rm.check_trade("AAPL", "BUY", 1, 10)
    assert "Sharpe ratio check failed" in caplog.text


def test_sortino_ratio_exception_branch(caplog):
    class Exploder(RiskManager):
        def sortino_ratio(self):
            raise Exception("boom sortino")

    rm = Exploder(sortino_min=1.0)
    caplog.set_level("ERROR")
    assert not rm.check_trade("AAPL", "BUY", 1, 10)
    assert "Sortino ratio check failed" in caplog.text
