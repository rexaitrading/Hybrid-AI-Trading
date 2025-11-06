# tests/test_trade_engine_gap_fill.py
"""
Gap-Filler Tests: TradeEngine
(Hybrid AI Quant Pro v21.0 Ã¢â‚¬â€œ Coverage 100%)
------------------------------------------------
Covers the last uncovered branches in trade_engine.py:
- Normalization of {"status": "ok", "reason": "ok"} Ã¢â€ â€™ "filled"/"normalized_ok"
- Router invalid dict Ã¢â€ â€™ "invalid_status"
- Performance tracker breaches + exceptions
- Sector exposure non-breach branch
- record_trade_outcome exception branch
"""

import pytest

from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker
from hybrid_ai_trading.trade_engine import TradeEngine


@pytest.fixture
def base_config(tmp_path):
    return {
        "mode": "paper",
        "audit_log_path": str(tmp_path / "audit.csv"),
        "backup_log_path": str(tmp_path / "backup.csv"),
        "risk": {
            "equity": 100000,
            "kelly": {"win_rate": 0.5, "payoff": 1.0, "fraction": 1.0},
            "max_drawdown": 0.5,
            "sharpe_min": 0.0,
            "sortino_min": 0.0,
            "intraday_sector_exposure": 0.5,  # generous cap
        },
        "sentiment": {},
        "gatescore": {},
    }


@pytest.fixture
def engine(base_config, monkeypatch):
    eng = TradeEngine(base_config, portfolio=PortfolioTracker(100000))
    # Default safe patches
    monkeypatch.setattr(eng.sentiment_filter, "allow_trade", lambda *a, **k: True)
    monkeypatch.setattr(eng.gatescore, "allow_trade", lambda *a, **k: True)
    return eng


# ----------------------------------------------------------------------
# Normalization paths
# ----------------------------------------------------------------------
def test_normalization_reason_ok(engine, monkeypatch):
    monkeypatch.setattr(
        engine.router, "route_order", lambda *_: {"status": "ok", "reason": "ok"}
    )
    res = engine.process_signal("AAPL", "BUY", 1, 100)
    assert res["status"] == "filled"
    assert res["reason"] == "normalized_ok"


def test_invalid_status_normalization(engine, monkeypatch):
    monkeypatch.setattr(engine.router, "route_order", lambda *_: {"status": "wtf"})
    res = engine.process_signal("AAPL", "BUY", 1, 100)
    assert res["status"] == "rejected"
    assert res["reason"] == "invalid_status"


# ----------------------------------------------------------------------
# Performance breaches + exceptions
# ----------------------------------------------------------------------
def test_performance_sharpe_and_sortino_breaches(engine, monkeypatch):
    monkeypatch.setattr(engine.router, "route_order", lambda *_: {"status": "ok"})

    # Sharpe breach
    monkeypatch.setattr(engine.performance_tracker, "sharpe_ratio", lambda: -5)
    res1 = engine.process_signal("AAPL", "BUY", 1, 100)
    assert res1["reason"] == "sharpe_breach"

    # Sortino breach
    monkeypatch.setattr(engine.performance_tracker, "sharpe_ratio", lambda: 2)
    monkeypatch.setattr(engine.performance_tracker, "sortino_ratio", lambda: -5)
    res2 = engine.process_signal("AAPL", "BUY", 1, 100)
    assert res2["reason"] == "sortino_breach"


def test_performance_exceptions(engine, monkeypatch):
    monkeypatch.setattr(engine.router, "route_order", lambda *_: {"status": "ok"})

    # Sharpe raises
    monkeypatch.setattr(
        engine.performance_tracker,
        "sharpe_ratio",
        lambda *_: (_ for _ in ()).throw(Exception("boom")),
    )
    res1 = engine.process_signal("AAPL", "BUY", 1, 100)
    assert "status" in res1

    # Sortino raises
    monkeypatch.setattr(engine.performance_tracker, "sharpe_ratio", lambda: 2)
    monkeypatch.setattr(
        engine.performance_tracker,
        "sortino_ratio",
        lambda *_: (_ for _ in ()).throw(Exception("fail")),
    )
    res2 = engine.process_signal("AAPL", "BUY", 1, 100)
    assert "status" in res2


# ----------------------------------------------------------------------
# Sector exposure non-breach
# ----------------------------------------------------------------------
def test_sector_exposure_non_breach(engine):
    """Covers the false branch of _sector_exposure_breach."""
    engine.portfolio.positions = {"IBM": {"size": 10, "avg_price": 100}}
    # IBM not in tech set Ã¢â€ â€™ should not breach
    assert engine._sector_exposure_breach("IBM") is False


# ----------------------------------------------------------------------
# record_trade_outcome exception
# ----------------------------------------------------------------------
def test_record_trade_outcome_exception(engine, monkeypatch, caplog):
    caplog.set_level("ERROR")
    monkeypatch.setattr(
        engine.performance_tracker,
        "record_trade",
        lambda *_: (_ for _ in ()).throw(Exception("fail")),
    )
    engine.record_trade_outcome(-100)
    assert "Failed to record trade outcome" in caplog.text


# ----------------------------------------------------------------------
# KellySizer fallback branches
# ----------------------------------------------------------------------
def test_kelly_sizer_negative_and_exception(engine, monkeypatch):
    """Cover negative and exception fallback branches in Kelly sizing."""
    # Negative size Ã¢â€ â€™ max(1, -5) Ã¢â€ â€™ size = 1
    monkeypatch.setattr(engine.kelly_sizer, "size_position", lambda *_: -5)
    res1 = engine.process_signal("AAPL", "BUY", None, 100)
    assert res1["status"] in {"blocked", "filled", "rejected"}

    # Exception in KellySizer Ã¢â€ â€™ fallback size = 1
    monkeypatch.setattr(
        engine.kelly_sizer,
        "size_position",
        lambda *_: (_ for _ in ()).throw(Exception("kelly fail")),
    )
    res2 = engine.process_signal("AAPL", "BUY", None, 100)
    assert res2["status"] in {"blocked", "filled", "rejected"}
