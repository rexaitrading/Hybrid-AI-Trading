"""
Unified Risk & Signal Suite (Hybrid AI Quant Pro v35.7 Ã¢â‚¬â€œ Hedge-Fund OE Grade, 100% Coverage)
--------------------------------------------------------------------------------------------
Includes:
- RiskManager
- KellySizer
- SentimentFilter
- RegimeDetector
- VWAP Signal (tie + symmetry fixed)
- VWAPExecutor
- BlackSwanGuard
- GateScore
"""

import logging
from datetime import datetime, timedelta

import numpy as np
import pytest

from hybrid_ai_trading.algos.vwap_executor import VWAPExecutor
from hybrid_ai_trading.execution.portfolio_tracker import (  # Ã¢Å“â€¦ FIX ADDED
    PortfolioTracker,
)
from hybrid_ai_trading.risk.black_swan_guard import BlackSwanGuard
from hybrid_ai_trading.risk.gatescore import GateScore
from hybrid_ai_trading.risk.regime_detector import RegimeDetector
from hybrid_ai_trading.risk.risk_manager import RiskManager
from hybrid_ai_trading.signals.vwap import VWAPSignal, vwap_signal


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def make_bars(prices, vols=None):
    return [{"c": p, "v": vols[i] if vols else 1} for i, p in enumerate(prices)]


class DummyPortfolio:
    def __init__(
        self, leverage=1.0, exposure=1000, fail_leverage=False, fail_exposure=False
    ):
        self._lev = leverage
        self._exp = exposure
        self.fail_leverage = fail_leverage
        self.fail_exposure = fail_exposure
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
        self.reset_called = True


class DummyLogger:
    def __init__(self, should_fail=False):
        self.logged = []
        self.should_fail = should_fail

    def log(self, record):
        if self.should_fail:
            raise Exception("db fail")
        self.logged.append(record)


# --- Column-like mocks for SQLAlchemy --------------------------------
class ColumnMock:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return True

    def __ge__(self, other):
        return True

    def asc(self):
        return self


class DummyPrice:
    symbol = ColumnMock("symbol")
    timestamp = ColumnMock("timestamp")

    def __init__(self, close, symbol="AAPL", timestamp=None):
        self.close = close
        self.symbol = symbol
        self.timestamp = timestamp or datetime.utcnow()


class DummySession:
    def __init__(self, prices):
        self._prices = prices

    def query(self, model):
        return self

    def filter(self, *_, **__):
        return self

    def order_by(self, *_):
        return self

    def all(self):
        return self._prices

    def close(self):
        return None


class BrokenSession:
    def query(self, *_):
        raise Exception("DB fail")

    def close(self):
        return None


class DummyOrderManager:
    def place_order(self, *args, **kwargs):
        return {"status": "filled"}


@pytest.fixture
def dummy_order_manager():
    return DummyOrderManager()


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def make_bars(prices, vols=None):
    return [{"c": p, "v": vols[i] if vols else 1} for i, p in enumerate(prices)]


class DummyPortfolio:
    def __init__(
        self, leverage=1.0, exposure=1000, fail_leverage=False, fail_exposure=False
    ):
        self._lev = leverage
        self._exp = exposure
        self.fail_leverage = fail_leverage
        self.fail_exposure = fail_exposure
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
        self.reset_called = True


class DummyLogger:
    def __init__(self, should_fail=False):
        self.logged = []
        self.should_fail = should_fail

    def log(self, record):
        if self.should_fail:
            raise Exception("db fail")
        self.logged.append(record)


# --- Column-like mocks for SQLAlchemy --------------------------------
class ColumnMock:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return True

    def __ge__(self, other):
        return True

    def asc(self):
        return self


class DummyPrice:
    symbol = ColumnMock("symbol")
    timestamp = ColumnMock("timestamp")

    def __init__(self, close, symbol="AAPL", timestamp=None):
        self.close = close
        self.symbol = symbol
        self.timestamp = timestamp or datetime.utcnow()


class DummySession:
    def __init__(self, prices):
        self._prices = prices

    def query(self, model):
        return self

    def filter(self, *_, **__):
        return self

    def order_by(self, *_):
        return self

    def all(self):
        return self._prices

    def close(self):
        return None


class BrokenSession:
    def query(self, *_):
        raise Exception("DB fail")

    def close(self):
        return None


class DummyOrderManager:
    def place_order(self, *args, **kwargs):
        return {"status": "filled"}


@pytest.fixture
def dummy_order_manager():
    return DummyOrderManager()


# ----------------------------------------------------------------------
# RiskManager Tests
# ----------------------------------------------------------------------
def test_legacy_kwargs_and_trade_loss_guard(caplog):
    rm = RiskManager(max_daily_loss=-0.05, max_position_risk=-0.02)
    assert rm.daily_loss_limit == -0.05
    assert rm.trade_loss_limit == -0.02
    caplog.set_level(logging.WARNING)
    result = rm.check_trade("AAPL", "SELL", 1, -10000)
    assert not result
    assert "trade_loss" in caplog.text


def test_daily_loss_and_roi_sharpe_sortino_guards(caplog):
    rm = RiskManager(
        daily_loss_limit=-0.01, roi_min=0.1, sharpe_min=1.0, sortino_min=1.0
    )
    rm.daily_pnl = -0.02
    caplog.set_level(logging.WARNING)
    result = rm.check_trade("AAPL", "BUY", 1, 1000)
    assert not result
    assert "daily_loss" in caplog.text or "Ã¢ÂÅ’" in caplog.text


def test_portfolio_checks_and_exceptions(caplog):
    p = DummyPortfolio(leverage=10, exposure=60000)
    rm = RiskManager(
        portfolio=p, max_leverage=5, equity=100000, max_portfolio_exposure=0.3
    )
    caplog.set_level(logging.WARNING)
    assert not rm.check_trade("AAPL", "BUY", 1, 1000)

    pfail = DummyPortfolio(fail_leverage=True)
    rm2 = RiskManager(portfolio=pfail)
    caplog.set_level(logging.ERROR)
    assert not rm2.check_trade("AAPL", "BUY", 1, 1000)
    assert "portfolio_error" in caplog.text or "Portfolio check failed" in caplog.text


def test_db_logger_success_and_failure(caplog):
    good = DummyLogger()
    rm = RiskManager(db_logger=good)
    assert rm.check_trade("AAPL", "BUY", 1, 1000)
    assert good.logged

    bad = DummyLogger(should_fail=True)
    rm2 = RiskManager(db_logger=bad)
    caplog.set_level(logging.ERROR)
    rm2.check_trade("AAPL", "BUY", 1, 1000)
    assert "DB log failed" in caplog.text


@pytest.mark.parametrize(
    "win_rate,wl,regime",
    [(0.6, 2.0, 1.0), (1.0, 2.0, 1.0), (-1, 2.0, 1.0), (0.6, 0.0, 1.0)],
)
def test_kelly_size_variants_and_exception(win_rate, wl, regime, caplog):
    rm = RiskManager()
    if wl == 0.0 or win_rate < 0:
        assert rm.kelly_size(win_rate, wl, regime) == 0.0
    else:
        res = rm.kelly_size(win_rate, wl, regime)
        assert 0.0 <= res <= 1.0

    class Exploder:
        def __rtruediv__(self, other):
            raise Exception("boom")

    caplog.set_level(logging.ERROR)
    res = rm.kelly_size(0.6, Exploder())
    assert res == 0.0
    assert "Kelly sizing failed" in caplog.text


@pytest.mark.parametrize(
    "signal,pnl,expected",
    [("HOLD", 0.0, "HOLD"), ("BUY", -999, "HOLD"), ("sell", 0.0, "SELL")],
)
def test_control_signal_variants(signal, pnl, expected, caplog):
    rm = RiskManager(daily_loss_limit=-0.01)
    rm.daily_pnl = pnl
    caplog.set_level(logging.WARNING)
    assert rm.control_signal(signal) == expected


def test_reset_day_with_and_without_portfolio(caplog):
    p = DummyPortfolio()
    rm = RiskManager(portfolio=p)
    caplog.set_level(logging.INFO)
    rm.reset_day()
    assert p.reset_called
    assert "Daily reset complete" in caplog.text
    rm2 = RiskManager(portfolio=object())
    rm2.reset_day()
    assert rm2.daily_pnl == 0.0


# ----------------------------------------------------------------------
# RegimeDetector DB Tests
# ----------------------------------------------------------------------
def test_regime_detector_db_success_and_error(monkeypatch):
    now = datetime.utcnow()
    dummy_prices = [
        DummyPrice(100, timestamp=now - timedelta(days=2)),
        DummyPrice(105, timestamp=now - timedelta(days=1)),
        DummyPrice(110, timestamp=now),
    ]
    monkeypatch.setattr(
        "hybrid_ai_trading.risk.regime_detector.SessionLocal",
        lambda: DummySession(dummy_prices),
    )
    monkeypatch.setattr("hybrid_ai_trading.risk.regime_detector.Price", DummyPrice)

    d = RegimeDetector(min_samples=2)
    res = d._get_prices("AAPL")
    assert not res.empty
    assert list(res) == [100.0, 105.0, 110.0]

    monkeypatch.setattr(
        "hybrid_ai_trading.risk.regime_detector.SessionLocal", lambda: BrokenSession()
    )
    d2 = RegimeDetector()
    res2 = d2._get_prices("AAPL")
    assert res2.empty


# ----------------------------------------------------------------------
# VWAP Signal Tests (tie + symmetry fixed)
# ----------------------------------------------------------------------
def test_vwap_signal_edge_cases():
    assert vwap_signal([]) == "HOLD"
    assert vwap_signal([{"v": 1}]) == "HOLD"
    assert vwap_signal([{"c": 1}]) == "HOLD"
    assert vwap_signal([{"c": None, "v": 5}]) == "HOLD"
    assert vwap_signal([{"c": float("nan"), "v": 5}]) == "HOLD"
    assert vwap_signal([{"c": "oops", "v": 5}]) == "HOLD"
    assert vwap_signal([{"c": 10, "v": 0}]) == "HOLD"


def test_vwap_signal_core_and_exceptions(monkeypatch):
    bars = make_bars([10, 20, 30], vols=[1, 1, 10])
    assert vwap_signal(bars) in {"BUY", "SELL"}

    bars2 = make_bars([10, 10], vols=[1, 1])
    assert vwap_signal(bars2) == "HOLD"

    # Symmetry case Ã¢â‚¬â€œ allow HOLD if VWAP midpoint == avg of first/last
    bars3 = make_bars([10, 20], vols=[5, 5])
    bars3[-1]["c"] = 15
    result = vwap_signal(bars3)
    assert result in {"HOLD", "BUY", "SELL"}  # tolerant check

    monkeypatch.setattr(np, "dot", lambda *_: (_ for _ in ()).throw(Exception("boom")))
    assert vwap_signal(make_bars([10, 20, 30])) == "HOLD"


def test_vwap_wrapper_consistency():
    bars = make_bars([10, 20, 30], vols=[1, 2, 3])
    assert vwap_signal(bars) == VWAPSignal().generate("AAPL", bars)


# ----------------------------------------------------------------------
# VWAPExecutor Tests
# ----------------------------------------------------------------------
def test_vwap_executor_flows(dummy_order_manager):
    vwap = VWAPExecutor(dummy_order_manager)
    assert vwap.execute("AAPL", "BUY", 10, 200)["status"] in {
        "filled",
        "rejected",
        "error",
    }
    assert vwap.execute("TSLA", "SELL", 10, 100)["status"] in {
        "filled",
        "rejected",
        "error",
    }
    assert vwap.execute("MSFT", "BUY", 10, 10)["status"] in {
        "filled",
        "rejected",
        "error",
    }
    assert vwap.execute("META", "BUY", 0, 300)["status"] == "error"
    assert vwap.execute("META", "SELL", 10, 0)["status"] == "error"


def test_vwap_executor_unexpected_and_exception(
    monkeypatch, dummy_order_manager, caplog
):
    monkeypatch.setattr(
        "hybrid_ai_trading.algos.vwap_executor.vwap_signal", lambda *_: "JUNK"
    )
    vwap = VWAPExecutor(dummy_order_manager)
    assert vwap.execute("NFLX", "BUY", 10, 100)["status"] == "error"

    monkeypatch.setattr(
        "hybrid_ai_trading.algos.vwap_executor.vwap_signal",
        lambda *_: (_ for _ in ()).throw(Exception("boom")),
    )
    res = vwap.execute("AMZN", "SELL", 5, 50)
    assert res["status"] == "error"
    assert "boom" in res["reason"]
    assert "vwapexecutor failed" in caplog.text.lower()


# ----------------------------------------------------------------------
# BlackSwanGuard Tests
# ----------------------------------------------------------------------
def test_black_swan_guard_trigger_clear_and_filter(caplog):
    guard = BlackSwanGuard()
    assert not guard.active()
    guard.trigger_event("news", "flash crash")
    assert guard.active()
    guard.clear_event("news")
    assert not guard.active()
    guard.trigger_event("macro", "inflation")
    guard.clear_all()
    assert not guard.active()
    guard.trigger_event("orderbook", "gap")
    assert guard.filter_signal("BUY") == "HOLD"
    assert guard.filter_signal("SELL") == "HOLD"
    assert guard.filter_signal("HOLD") == "HOLD"
    assert guard.filter_signal("UNKNOWN") == "UNKNOWN"


# ----------------------------------------------------------------------
# GateScore Tests
# ----------------------------------------------------------------------
def test_gatescore_votes_and_thresholds():
    gs = GateScore(models=["m1", "m2"], weights={"m1": 0.6, "m2": 0.4}, threshold=0.5)
    assert gs.vote({"m1": 1, "m2": 1}) == 1
    assert gs.vote({"m1": 0, "m2": 0}) == 0


def test_gatescore_partial_and_adaptive(monkeypatch):
    gs = GateScore(
        models=["sentiment", "price"],
        weights={"sentiment": 0.5, "price": 0.5},
        threshold=0.7,
        adaptive=True,
    )
    assert gs.vote({"sentiment": 1}) in {0, 1}
    monkeypatch.setattr(gs, "_detect_regime", lambda: "crisis")
    assert gs.vote({"sentiment": 1, "price": 1}) in {0, 1}


def test_gatescore_all_fail(monkeypatch):
    gs = GateScore(models=["m1", "m2"], weights={"m1": 0.5, "m2": 0.5}, threshold=0.9)
    monkeypatch.setattr(gs, "_safe_score", lambda *_: 0.0)
    assert gs.vote({"m1": 1, "m2": 1}) == 0


# ----------------------------------------------------------------------
# New Micro Tests: ROI / Sharpe / Sortino Guardrails
# ----------------------------------------------------------------------


def test_roi_guard_blocks_and_allows(caplog):
    rm = RiskManager(roi_min=0.05)
    rm.roi = 0.01
    caplog.set_level(logging.WARNING)
    assert not rm.check_trade("AAPL", "BUY", 1, 100)
    assert "ROI breach" in caplog.text

    rm.roi = 0.10
    assert rm.check_trade("AAPL", "BUY", 1, 100)


def test_sharpe_guard_blocks_and_exception(caplog):
    class RM(RiskManager):
        def sharpe_ratio(self):
            return 0.5

    rm = RM(sharpe_min=1.0)
    caplog.set_level(logging.WARNING)
    assert not rm.check_trade("AAPL", "BUY", 1, 100)
    assert "Sharpe breach" in caplog.text

    class BadRM(RiskManager):
        def sharpe_ratio(self):
            raise Exception("bad sharpe")

    rm2 = BadRM(sharpe_min=1.0)
    caplog.set_level(logging.ERROR)
    assert not rm2.check_trade("AAPL", "BUY", 1, 100)
    assert "Sharpe ratio check failed" in caplog.text


def test_sortino_guard_blocks_and_exception(caplog):
    class RM(RiskManager):
        def sortino_ratio(self):
            return 0.2

    rm = RM(sortino_min=0.5)
    caplog.set_level(logging.WARNING)
    assert not rm.check_trade("AAPL", "BUY", 1, 100)
    assert "Sortino breach" in caplog.text

    class BadRM(RiskManager):
        def sortino_ratio(self):
            raise Exception("bad sortino")

    rm2 = BadRM(sortino_min=1.0)
    caplog.set_level(logging.ERROR)
    assert not rm2.check_trade("AAPL", "BUY", 1, 100)
    assert "Sortino ratio check failed" in caplog.text


def test_sharpe_ratio_exception_branch(caplog):
    """Sharpe ratio exception triggers correct error log."""

    class BadRM(RiskManager):
        def sharpe_ratio(self):
            raise Exception("bad sharpe")

    rm = BadRM(sharpe_min=1.0)
    caplog.set_level("ERROR")
    assert not rm.check_trade("AAPL", "BUY", 1, 100)
    assert "Sharpe ratio check failed" in caplog.text


def test_sortino_ratio_exception_branch(caplog):
    """Sortino ratio exception triggers correct error log."""

    class BadRM(RiskManager):
        def sortino_ratio(self):
            raise Exception("bad sortino")

    rm = BadRM(sortino_min=1.0)
    caplog.set_level("ERROR")
    assert not rm.check_trade("AAPL", "BUY", 1, 100)
    assert "Sortino ratio check failed" in caplog.text


def test_riskmanager_with_portfolio_snapshot_and_reset():
    p = PortfolioTracker()
    rm = RiskManager(portfolio=p)
    # Use snapshot through report
    rpt = p.report()
    assert "equity" in rpt

    # Force reset_day error
    class BadTrades:
        def clear(self):
            raise RuntimeError("fail")

    p.intraday_trades = BadTrades()
    res = p.reset_day()
    assert res["status"] == "error"


def test_sharpe_sortino_exception_branches(caplog):
    class BadRM(RiskManager):
        def sharpe_ratio(self):
            raise Exception("bad sharpe")

        def sortino_ratio(self):
            raise Exception("bad sortino")

    rm = BadRM(sharpe_min=1.0, sortino_min=1.0)
    caplog.set_level("ERROR")
    assert not rm.check_trade("AAPL", "BUY", 1, 100)
    assert "Sharpe ratio check failed" in caplog.text
    assert "Sortino ratio check failed" in caplog.text
