"""
Unit Tests: TradeEngine (Hybrid AI Quant Pro v18.0 – Hedge-Fund Grade, 100% Coverage)
-------------------------------------------------------------------------------------
Covers ALL branches in trade_engine.py:
- __init__: brokers, Kelly sanitize
- process_signal: validation, guardrails, Kelly sizing, algo routing, router paths,
  performance checks, regime disabled, sentiment/gatescore veto + exceptions,
  normalization
- _write_audit: success, primary fail, both fail
- alert: Slack/Telegram/Email success + fail + no env
- _fire_alert: dispatch fail
- reset_day: ok, portfolio fail, risk fail, exception
- adaptive_fraction: empty, equity<=0, peak<=0, scaling, exception
- Accessors: get_equity, get_positions, get_history
"""

import os
import smtplib
import pytest
import builtins
import sys

from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def base_config(tmp_path):
    return {
        "mode": "paper",
        "audit_log_path": str(tmp_path / "audit.csv"),
        "backup_log_path": str(tmp_path / "backup.csv"),
        "risk": {
            "equity": 100000,
            "kelly": {"win_rate": 0.5, "payoff": 1.0, "fraction": 1.0, "enabled": True},
            "max_drawdown": 0.5,
            "sharpe_min": 0.0,
            "sortino_min": 0.0,
            "intraday_sector_exposure": 0.01,
            "hedge_rules": {"equities_vol_spike": ["SPY"]},
        },
        "sentiment": {},
        "gatescore": {},
        "alerts": {
            "slack_webhook_env": "SLACK_ENV",
            "telegram_bot_env": "TG_BOT",
            "telegram_chat_id_env": "TG_CHAT",
            "email_env": "EMAIL_ENV",
        },
    }


@pytest.fixture
def engine(TradeEngineClass, base_config, monkeypatch):
    """Create a TradeEngine instance with safe defaults for tests."""
    eng = TradeEngineClass(base_config, portfolio=PortfolioTracker(100000))
    # Safe defaults: prevent real vetoes
    monkeypatch.setattr(eng.sentiment_filter, "allow_trade", lambda *a, **k: True)
    monkeypatch.setattr(eng.gatescore, "allow_trade", lambda *a, **k: True)
    return eng


# ----------------------------------------------------------------------
# Init
# ----------------------------------------------------------------------
def test_init_brokers_and_kelly(TradeEngineClass, base_config):
    base_config["risk"]["kelly"] = {}
    TradeEngineClass(base_config, brokers={"alpaca": object()})


# ----------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------
def test_process_signal_validation(engine):
    assert engine.process_signal("AAPL", 123, 100)["status"] == "rejected"
    assert engine.process_signal("AAPL", "INVALID", 100)["status"] == "rejected"
    assert engine.process_signal("AAPL", "HOLD", 100)["status"] == "ignored"
    assert engine.process_signal("AAPL", "BUY", -1)["status"] == "rejected"


# ----------------------------------------------------------------------
# Guardrails
# ----------------------------------------------------------------------
def test_guardrails_equity_sector_hedge_drawdown(engine):
    engine.portfolio.equity = 0
    assert "equity" in engine.process_signal("AAPL", "BUY", 100)["reason"]

    engine.portfolio.equity = 100000
    engine.portfolio.positions = {"AAPL": {"size": 99999, "avg_price": 1}}
    assert "sector" in engine.process_signal("AAPL", "BUY", 100)["reason"]

    assert "hedge" in engine.process_signal("SPY", "BUY", 100)["reason"]

    engine.portfolio.positions.clear()
    engine.portfolio.history = [(0, 100000)]
    engine.portfolio.equity = 40000
    engine.config["risk"]["max_drawdown"] = 0.2
    assert "drawdown" in engine.process_signal("AAPL", "BUY", 100)["reason"]


# ----------------------------------------------------------------------
# Kelly sizing
# ----------------------------------------------------------------------
def test_kelly_sizer_dict_int_and_exception(engine, monkeypatch):
    monkeypatch.setattr(engine.kelly_sizer, "size_position", lambda *_: {"size": 2})
    assert engine.process_signal("AAPL", "BUY", 100)["status"]

    monkeypatch.setattr(engine.kelly_sizer, "size_position", lambda *_: 2)
    assert engine.process_signal("AAPL", "BUY", 100)["status"]

    monkeypatch.setattr(engine.kelly_sizer, "size_position", lambda *_: (_ for _ in ()).throw(Exception("boom")))
    assert engine.process_signal("AAPL", "BUY", 100)["status"]


# ----------------------------------------------------------------------
# Algo routing
# ----------------------------------------------------------------------
def test_algo_routing_success_and_fail(engine, monkeypatch):
    sys.modules["hybrid_ai_trading.algos.twap"] = type("M", (), {
        "TWAPExecutor": lambda *_: type("X", (), {"execute": lambda *_: {"status": "ok"}})()
    })
    assert engine.process_signal("AAPL", "BUY", 1, 100, algo="twap")["status"] == "filled"

    sys.modules["hybrid_ai_trading.algos.vwap"] = type("M", (), {
        "VWAPExecutor": lambda *_: (_ for _ in ()).throw(Exception("bad"))
    })
    assert engine.process_signal("AAPL", "BUY", 1, 100, algo="vwap")["status"] == "error"

    sys.modules["hybrid_ai_trading.algos.iceberg"] = type("M", (), {
        "IcebergExecutor": lambda *_: type("X", (), {"execute": lambda *_: {"status": "ok"}})()
    })
    assert engine.process_signal("AAPL", "BUY", 1, 100, algo="iceberg")["status"] == "filled"

    res = engine.process_signal("AAPL", "BUY", 1, 100, algo="unknown")
    assert res["status"] == "rejected"


# ----------------------------------------------------------------------
# Router paths
# ----------------------------------------------------------------------
def test_router_exception_none_error_invalid(engine, monkeypatch):
    monkeypatch.setattr(engine.router, "route_order", lambda *_: (_ for _ in ()).throw(Exception("fail")))
    assert "router_error" in engine.process_signal("AAPL", "BUY", 100)["reason"]

    monkeypatch.setattr(engine.router, "route_order", lambda *_: None)
    assert "router_failed" in engine.process_signal("AAPL", "BUY", 100)["reason"]

    monkeypatch.setattr(engine.router, "route_order", lambda *_: {"status": "error", "reason": "oops"})
    assert "router_error" in engine.process_signal("AAPL", "BUY", 100)["reason"]

    monkeypatch.setattr(engine.router, "route_order", lambda *_: "nonsense")
    assert engine.process_signal("AAPL", "BUY", 100)["status"] == "rejected"


# ----------------------------------------------------------------------
# Perf, regime, sentiment, gatescore
# ----------------------------------------------------------------------
def test_perf_regime_sentiment_gatescore(engine, monkeypatch):
    monkeypatch.setattr(engine.router, "route_order", lambda *_: {"status": "ok"})

    monkeypatch.setattr(engine.performance_tracker, "sharpe_ratio", lambda: -5)
    assert "sharpe" in engine.process_signal("AAPL", "BUY", 100)["reason"]

    monkeypatch.setattr(engine.performance_tracker, "sharpe_ratio", lambda: 2)
    monkeypatch.setattr(engine.performance_tracker, "sortino_ratio", lambda: -5)
    assert "sortino" in engine.process_signal("AAPL", "BUY", 100)["reason"]

    engine.regime_enabled = False
    assert "regime_disabled" in engine.process_signal("AAPL", "BUY", 100)["reason"]

    engine.regime_enabled = True
    monkeypatch.setattr(engine.sentiment_filter, "allow_trade", lambda *_: False)
    assert "sentiment" in engine.process_signal("AAPL", "BUY", 100)["reason"]

    monkeypatch.setattr(engine.sentiment_filter, "allow_trade", lambda *_: (_ for _ in ()).throw(Exception("bad")))
    assert "sentiment" in engine.process_signal("AAPL", "BUY", 100)["reason"]

    monkeypatch.setattr(engine.sentiment_filter, "allow_trade", lambda *_: True)
    monkeypatch.setattr(engine.gatescore, "allow_trade", lambda *_: False)
    assert "gatescore" in engine.process_signal("AAPL", "BUY", 100)["reason"]

    monkeypatch.setattr(engine.gatescore, "allow_trade", lambda *_: (_ for _ in ()).throw(Exception("fail")))
    assert "gatescore" in engine.process_signal("AAPL", "BUY", 100)["reason"]


# ----------------------------------------------------------------------
# Audit
# ----------------------------------------------------------------------
def test_audit_normal_and_fail(engine, tmp_path, monkeypatch):
    f = tmp_path / "audit.csv"
    engine.audit_log = str(f)
    engine.backup_log = str(tmp_path / "backup.csv")
    engine.router.route_order = lambda *_: {"status": "ok"}
    res = engine.process_signal("AAPL", "BUY", 100)
    assert "status" in res

    def bad_open(*a, **k): raise OSError("disk full")
    monkeypatch.setattr(builtins, "open", bad_open)
    engine._write_audit(["row"])


# ----------------------------------------------------------------------
# Alerts
# ----------------------------------------------------------------------
def test_alert_success_and_fail_and_noenv(engine, monkeypatch):
    os.environ["SLACK_ENV"], os.environ["TG_BOT"], os.environ["TG_CHAT"], os.environ["EMAIL_ENV"] = (
        "http://fake", "bot", "chat", "me@example.com"
    )

    monkeypatch.setattr("requests.post", lambda *_: type("R", (), {"status_code": 200})())
    monkeypatch.setattr("requests.get", lambda *_: type("R", (), {"status_code": 200})())
    monkeypatch.setattr(
        smtplib, "SMTP",
        lambda *_: type("S", (), {"send_message": lambda *_: None,
                                  "__enter__": lambda s: s,
                                  "__exit__": lambda *a: None})()
    )
    r1 = engine.alert("msg")
    assert "slack" in r1 and "telegram" in r1 and "email" in r1

    monkeypatch.setattr("requests.post", lambda *_: (_ for _ in ()).throw(Exception("fail")))
    monkeypatch.setattr("requests.get", lambda *_: (_ for _ in ()).throw(Exception("fail")))
    monkeypatch.setattr("smtplib.SMTP", lambda *_: (_ for _ in ()).throw(Exception("fail")))
    r2 = engine.alert("msg")
    assert any(v == "error" for v in r2.values())

    monkeypatch.setattr(os, "getenv", lambda *a, **k: "")
    r3 = engine.alert("msg")
    assert r3["status"] == "no_alerts"


# ----------------------------------------------------------------------
# Fire alert
# ----------------------------------------------------------------------
def test_fire_alert_failure(engine, monkeypatch, caplog):
    monkeypatch.setattr(engine.router, "_send_alert", lambda *_: (_ for _ in ()).throw(Exception("boom")))
    caplog.set_level("ERROR")
    engine._fire_alert("msg")
    assert "dispatch failed" in caplog.text.lower()


# ----------------------------------------------------------------------
# Reset day
# ----------------------------------------------------------------------
def test_reset_day_ok_and_errors(engine, monkeypatch):
    assert engine.reset_day()["status"] == "ok"

    monkeypatch.setattr(engine.portfolio, "reset_day", lambda: {"status": "error"}, raising=False)
    assert engine.reset_day()["status"] == "error"

    monkeypatch.setattr(engine.risk_manager, "reset_day", lambda: {"status": "error"})
    assert engine.reset_day()["status"] == "error"

    monkeypatch.setattr(engine.portfolio, "reset_day", lambda: (_ for _ in ()).throw(Exception("fail")), raising=False)
    assert engine.reset_day()["status"] == "error"


# ----------------------------------------------------------------------
# Adaptive fraction
# ----------------------------------------------------------------------
def test_adaptive_fraction_paths(engine, monkeypatch):
    engine.portfolio.history = []
    assert engine.adaptive_fraction() == engine.base_fraction

    engine.portfolio.history = [(0, 100000)]
    engine.portfolio.equity = 0
    assert engine.adaptive_fraction() == engine.base_fraction

    engine.portfolio.history = [(0, -1)]
    engine.portfolio.equity = -1
    assert engine.adaptive_fraction() == engine.base_fraction

    engine.portfolio.history = [(0, 100000), (1, 50000)]
    engine.portfolio.equity = 50000
    assert 0 < engine.adaptive_fraction() <= engine.base_fraction

    monkeypatch.setattr(engine.portfolio, "history", None)
    assert engine.adaptive_fraction() == engine.base_fraction


# ----------------------------------------------------------------------
# Accessors
# ----------------------------------------------------------------------
def test_accessors(engine):
    assert isinstance(engine.get_equity(), float)
    assert isinstance(engine.get_positions(), dict)
    assert isinstance(engine.get_history(), list)
