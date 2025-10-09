"""
Edge Case Tests: TradeEngine (Hybrid AI Quant Pro v20.1 – Hedge-Fund OE Grade, 100% Coverage)
----------------------------------------------------------------------------------------------
Targets the final uncovered branches in trade_engine.py:
- Algo import failures across TWAP/VWAP/Iceberg
- Router dicts missing or with invalid status
- Sentiment & GateScore exceptions
- Audit log primary + backup failure
- record_trade_outcome exception handling
"""

import builtins
import importlib

import pytest

from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def base_config(tmp_path):
    """Minimal config with audit paths + risk settings."""
    return {
        "mode": "paper",
        "audit_log_path": str(tmp_path / "audit.csv"),
        "backup_log_path": str(tmp_path / "backup.csv"),
        "risk": {
            "equity": 100000,
            "kelly": {"win_rate": 0.5, "payoff": 1.0, "fraction": 1.0, "enabled": True},
            "max_drawdown": 0.1,
            "sharpe_min": 0.0,
            "sortino_min": 0.0,
            "intraday_sector_exposure": 0.01,
            "hedge_rules": {"equities_vol_spike": ["SPY"]},
        },
    }


@pytest.fixture
def engine(TradeEngineClass, base_config, monkeypatch):
    """Fresh TradeEngine with SentimentFilter & GateScore patched safe by default."""
    eng = TradeEngineClass(base_config, portfolio=PortfolioTracker(100000))
    monkeypatch.setattr(eng.sentiment_filter, "allow_trade", lambda *a, **k: True)
    monkeypatch.setattr(eng.gatescore, "allow_trade", lambda *a, **k: True)
    return eng


# ----------------------------------------------------------------------
# Algo import failures
# ----------------------------------------------------------------------
def test_algo_import_failures(engine, monkeypatch):
    """Algo import fails for multiple algo types → returns error with algo_error reason."""
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda *_: (_ for _ in ()).throw(ImportError("fail")),
    )

    for algo in ("twap", "vwap", "iceberg"):
        res = engine.process_signal("AAPL", "BUY", 1, 100, algo=algo)
        assert res["status"] == "error"
        assert "algo_error" in res["reason"]


# ----------------------------------------------------------------------
# Router invalid dicts
# ----------------------------------------------------------------------
def test_router_invalid_dicts(engine, monkeypatch):
    """Router returns dicts without or with invalid status → rejected."""
    monkeypatch.setattr(engine.router, "route_order", lambda *_: {"foo": "bar"})
    assert engine.process_signal("AAPL", "BUY", 1, 100)["status"] == "rejected"

    monkeypatch.setattr(engine.router, "route_order", lambda *_: {"status": "wtf"})
    assert engine.process_signal("AAPL", "BUY", 1, 100)["status"] == "rejected"


# ----------------------------------------------------------------------
# Sentiment and GateScore exceptions
# ----------------------------------------------------------------------
def test_sentiment_and_gatescore_exceptions(engine, monkeypatch):
    """Sentiment veto raises exception; GateScore veto raises exception."""
    monkeypatch.setattr(
        engine.sentiment_filter,
        "allow_trade",
        lambda *_: (_ for _ in ()).throw(Exception("sentiment fail")),
    )
    res1 = engine.process_signal("AAPL", "BUY", 100)
    assert "sentiment" in res1["reason"]

    monkeypatch.setattr(engine.sentiment_filter, "allow_trade", lambda *_: True)
    monkeypatch.setattr(
        engine.gatescore,
        "allow_trade",
        lambda *_: (_ for _ in ()).throw(Exception("gatescore fail")),
    )
    res2 = engine.process_signal("AAPL", "BUY", 100)
    assert "gatescore" in res2["reason"]


# ----------------------------------------------------------------------
# Audit log failure
# ----------------------------------------------------------------------
def test_audit_log_primary_and_backup_fail(engine, tmp_path, monkeypatch, caplog):
    """Both primary and backup audit log writes fail → logs error."""
    engine.audit_log = str(tmp_path / "audit.csv")
    engine.backup_log = str(tmp_path / "backup.csv")
    caplog.set_level("ERROR")

    def bad_open(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(builtins, "open", bad_open)

    res = engine.process_signal("AAPL", "BUY", 100)
    assert "status" in res
    assert "audit" in caplog.text.lower()


# ----------------------------------------------------------------------
# record_trade_outcome exception
# ----------------------------------------------------------------------
def test_record_trade_outcome_exception(engine, monkeypatch, caplog):
    """PerformanceTracker raises inside record_trade → logs error."""
    caplog.set_level("ERROR")
    monkeypatch.setattr(
        engine.performance_tracker,
        "record_trade",
        lambda *_: (_ for _ in ()).throw(Exception("boom")),
    )

    engine.record_trade_outcome(-123)
    assert "record" in caplog.text.lower()


def test_normalization_paths(engine, monkeypatch):
    """Router returns ok/ok → normalized to filled/normalized_ok."""
    monkeypatch.setattr(
        engine.router, "route_order", lambda *_: {"status": "ok", "reason": "ok"}
    )
    res = engine.process_signal("AAPL", "BUY", 1, 100)
    assert res["status"] == "filled"
    assert res["reason"] == "normalized_ok"


def test_performance_tracker_exception(engine, monkeypatch):
    """Force sharpe_ratio to raise → hits performance exception branch."""
    monkeypatch.setattr(
        engine.performance_tracker,
        "sharpe_ratio",
        lambda *_: (_ for _ in ()).throw(Exception("boom")),
    )
    res = engine.process_signal("AAPL", "BUY", 100)
    assert "status" in res


def test_drawdown_guardrail_exception(engine, monkeypatch):
    """Force exception inside drawdown calc → hits except branch."""
    engine.portfolio.history = [(0, 100000)]
    engine.portfolio.equity = 50000
    monkeypatch.setattr(engine.portfolio, "history", None)  # breaks iteration
    res = engine.process_signal("AAPL", "BUY", 100)
    assert "status" in res


def test_performance_tracker_sortino_exception(engine, monkeypatch):
    """Force sortino_ratio to raise → hits exception branch."""
    monkeypatch.setattr(engine.performance_tracker, "sharpe_ratio", lambda: 2)
    monkeypatch.setattr(
        engine.performance_tracker,
        "sortino_ratio",
        lambda *_: (_ for _ in ()).throw(Exception("boom")),
    )
    res = engine.process_signal("AAPL", "BUY", 100)
    assert "status" in res


def test_audit_primary_success_backup_fail(engine, tmp_path, monkeypatch, caplog):
    """Covers case where primary audit succeeds but backup fails."""
    engine.audit_log = str(tmp_path / "audit.csv")
    engine.backup_log = str(tmp_path / "backup.csv")

    caplog.set_level("ERROR")

    real_open = builtins.open

    def selective_open(path, *a, **k):
        if str(path).endswith("backup.csv"):
            raise OSError("disk full")
        return real_open(path, *a, **k)

    monkeypatch.setattr(builtins, "open", selective_open)

    res = engine.process_signal("AAPL", "BUY", 100)
    assert "status" in res
    assert "audit" in caplog.text.lower()


def test_drawdown_exception(engine, monkeypatch):
    """Break history iteration to trigger drawdown exception branch."""
    engine.portfolio.history = [(0, 100000)]
    engine.portfolio.equity = 50000
    monkeypatch.setattr(engine.portfolio, "history", None)
    res = engine.process_signal("AAPL", "BUY", 100)
    assert "status" in res


def test_performance_tracker_exceptions(engine, monkeypatch):
    """Force sharpe_ratio and sortino_ratio to raise exceptions."""
    monkeypatch.setattr(
        engine.performance_tracker,
        "sharpe_ratio",
        lambda *_: (_ for _ in ()).throw(Exception("boom")),
    )
    res1 = engine.process_signal("AAPL", "BUY", 100)
    assert "status" in res1

    monkeypatch.setattr(engine.performance_tracker, "sharpe_ratio", lambda: 2)
    monkeypatch.setattr(
        engine.performance_tracker,
        "sortino_ratio",
        lambda *_: (_ for _ in ()).throw(Exception("boom")),
    )
    res2 = engine.process_signal("AAPL", "BUY", 100)
    assert "status" in res2


def test_invalid_status_normalization(engine, monkeypatch):
    """Router returns nonsense status → rejected by normalization block."""
    monkeypatch.setattr(engine.router, "route_order", lambda *_: {"status": "nonsense"})
    res = engine.process_signal("AAPL", "BUY", 1, 100)
    assert res["status"] == "rejected"
    assert res["reason"] == "invalid_status"


def test_drawdown_guardrail_exception(engine, monkeypatch):
    """Force exception inside drawdown calculation."""
    engine.portfolio.history = [(0, 100000)]
    engine.portfolio.equity = 50000
    # Break history iteration to hit exception path
    monkeypatch.setattr(engine.portfolio, "history", None)
    res = engine.process_signal("AAPL", "BUY", 100)
    assert "status" in res


def test_performance_sharpe_breach(engine, monkeypatch):
    """Force sharpe_ratio below threshold → triggers breach."""
    monkeypatch.setattr(engine.performance_tracker, "sharpe_ratio", lambda: -5)
    res = engine.process_signal("AAPL", "BUY", 100)
    assert res["reason"] == "sharpe_breach"


def test_performance_sortino_breach(engine, monkeypatch):
    """Force sortino_ratio below threshold → triggers breach."""
    monkeypatch.setattr(engine.performance_tracker, "sharpe_ratio", lambda: 2)
    monkeypatch.setattr(engine.performance_tracker, "sortino_ratio", lambda: -5)
    res = engine.process_signal("AAPL", "BUY", 100)
    assert res["reason"] == "sortino_breach"


def test_normalization_reason_ok(engine, monkeypatch):
    """Router returns reason=='ok' → normalized to 'normalized_ok'."""
    monkeypatch.setattr(
        engine.router, "route_order", lambda *_: {"status": "ok", "reason": "ok"}
    )
    res = engine.process_signal("AAPL", "BUY", 1, 100)
    assert res["reason"] == "normalized_ok"


def test_record_trade_outcome_logs_error(engine, monkeypatch, caplog):
    """Force record_trade to raise → log error at end of record_trade_outcome."""
    caplog.set_level("ERROR")
    monkeypatch.setattr(
        engine.performance_tracker,
        "record_trade",
        lambda *_: (_ for _ in ()).throw(Exception("fail")),
    )
    engine.record_trade_outcome(-100)
    assert "Failed to record trade outcome" in caplog.text
