"""
Micro Tests: TradeEngine (Hybrid AI Quant Pro v20.0 – Hedge-Fund OE Grade, 100% Coverage)
-----------------------------------------------------------------------------------------
Covers every uncovered branch in trade_engine.py:
- alert(): success + all fail + no env
- KellySizer: dict/int/weird/negative/exception returns
- Guardrails: equity depleted, sector exposure, hedge trigger
- Sentiment & GateScore: veto + exceptions
- Router: invalid dicts + nonsense
- _write_audit: failures
- record_trade_outcome: exception branch
"""

import builtins
import os
import smtplib

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
        "alerts": {
            "slack_webhook_env": "SLACK_ENV",
            "telegram_bot_env": "TG_BOT",
            "telegram_chat_id_env": "TG_CHAT",
            "email_env": "EMAIL_ENV",
        },
    }


@pytest.fixture
def engine(TradeEngineClass, base_config, monkeypatch):
    """
    Fresh TradeEngine instance with patched SentimentFilter/GateScore
    so only explicit veto/exception paths trigger.
    """
    eng = TradeEngineClass(base_config, portfolio=PortfolioTracker(100000))
    monkeypatch.setattr(eng.sentiment_filter, "allow_trade", lambda *a, **k: True)
    monkeypatch.setattr(eng.gatescore, "allow_trade", lambda *a, **k: True)
    return eng


@pytest.fixture
def portfolio():
    """Standalone PortfolioTracker for tests that require it."""
    return PortfolioTracker(100000)


# ----------------------------------------------------------------------
# alert()
# ----------------------------------------------------------------------
def test_alert_success_and_fail_and_noenv(engine, monkeypatch, caplog):
    """Covers Slack/Telegram/Email success, failures, and no-env branch."""
    os.environ["SLACK_ENV"] = "fake"
    os.environ["TG_BOT"] = "bot"
    os.environ["TG_CHAT"] = "chat"
    os.environ["EMAIL_ENV"] = "me@example.com"

    # Success path
    monkeypatch.setattr("requests.post", lambda *a, **k: type("R", (), {"status_code": 200})())
    monkeypatch.setattr("requests.get", lambda *a, **k: type("R", (), {"status_code": 200})())
    monkeypatch.setattr(
        smtplib,
        "SMTP",
        lambda *_: type(
            "S",
            (),
            {
                "send_message": lambda *_: None,
                "__enter__": lambda s: s,
                "__exit__": lambda *a: None,
            },
        )(),
    )
    res1 = engine.alert("ok")
    assert res1["slack"] == 200 and res1["telegram"] == 200 and res1["email"] == "sent"

    # All fail
    caplog.set_level("ERROR")
    monkeypatch.setattr(
        "requests.post", lambda *a, **k: (_ for _ in ()).throw(Exception("slack fail"))
    )
    monkeypatch.setattr("requests.get", lambda *a, **k: (_ for _ in ()).throw(Exception("tg fail")))
    monkeypatch.setattr(
        smtplib, "SMTP", lambda *a, **k: (_ for _ in ()).throw(Exception("email fail"))
    )
    res2 = engine.alert("fail")
    assert res2["slack"] == "error" and res2["telegram"] == "error" and res2["email"] == "error"
    assert "slack" in caplog.text.lower()
    assert "telegram" in caplog.text.lower()
    assert "email" in caplog.text.lower()

    # No envs
    monkeypatch.setattr(os, "getenv", lambda *a, **k: "")
    res3 = engine.alert("msg")
    assert res3["status"] == "no_alerts"


# ----------------------------------------------------------------------
# KellySizer
# ----------------------------------------------------------------------
def test_kelly_sizer_variants(engine, monkeypatch):
    """Covers dict/int/weird/negative/exception return branches."""
    monkeypatch.setattr(engine.kelly_sizer, "size_position", lambda *_: {"size": 5})
    assert "status" in engine.process_signal("AAPL", "BUY", 100)

    monkeypatch.setattr(engine.kelly_sizer, "size_position", lambda *_: 2)
    assert "status" in engine.process_signal("AAPL", "BUY", 100)

    monkeypatch.setattr(engine.kelly_sizer, "size_position", lambda *_: "weird")
    assert "status" in engine.process_signal("AAPL", "BUY", 100)

    monkeypatch.setattr(engine.kelly_sizer, "size_position", lambda *_: -5)
    assert "status" in engine.process_signal("AAPL", "BUY", 100)

    monkeypatch.setattr(
        engine.kelly_sizer,
        "size_position",
        lambda *_: (_ for _ in ()).throw(Exception("boom")),
    )
    assert "status" in engine.process_signal("AAPL", "BUY", 100)


# ----------------------------------------------------------------------
# Guardrails
# ----------------------------------------------------------------------
def test_sector_and_hedge_guardrails(engine):
    """Covers equity depletion, sector exposure breach, hedge trigger."""
    engine.portfolio.equity = 0
    assert "equity" in engine.process_signal("AAPL", "BUY", 100)["reason"]

    engine.portfolio.equity = 100000
    engine.portfolio.positions = {"AAPL": {"size": 99999, "avg_price": 1}}
    assert "sector" in engine.process_signal("AAPL", "BUY", 100)["reason"]

    engine.config["risk"]["hedge_rules"] = {"equities_vol_spike": ["SPY"]}
    res = engine.process_signal("SPY", "BUY", 100)
    assert "hedge" in res["reason"]


# ----------------------------------------------------------------------
# Sentiment & GateScore
# ----------------------------------------------------------------------
def test_sentiment_and_gatescore_veto_and_exceptions(engine, monkeypatch):
    """Covers veto and exception branches for sentiment & gatescore filters."""
    monkeypatch.setattr(engine.sentiment_filter, "allow_trade", lambda *_: False)
    assert "sentiment" in engine.process_signal("AAPL", "BUY", 100)["reason"]

    monkeypatch.setattr(
        engine.sentiment_filter,
        "allow_trade",
        lambda *_: (_ for _ in ()).throw(Exception("bad sentiment")),
    )
    assert "sentiment" in engine.process_signal("AAPL", "BUY", 100)["reason"]

    monkeypatch.setattr(engine.sentiment_filter, "allow_trade", lambda *_: True)
    monkeypatch.setattr(engine.gatescore, "allow_trade", lambda *_: False)
    assert "gatescore" in engine.process_signal("AAPL", "BUY", 100)["reason"]

    monkeypatch.setattr(
        engine.gatescore,
        "allow_trade",
        lambda *_: (_ for _ in ()).throw(Exception("bad gs")),
    )
    assert "gatescore" in engine.process_signal("AAPL", "BUY", 100)["reason"]


# ----------------------------------------------------------------------
# Router invalid outputs
# ----------------------------------------------------------------------
def test_router_invalid_variants(engine, monkeypatch):
    """Covers router returning dicts missing/invalid 'status' keys."""
    monkeypatch.setattr(engine.router, "route_order", lambda *_: {"foo": "bar"})
    assert engine.process_signal("AAPL", "BUY", 100)["status"] == "rejected"

    monkeypatch.setattr(engine.router, "route_order", lambda *_: {"status": "wtf"})
    assert engine.process_signal("AAPL", "BUY", 100)["status"] == "rejected"


# ----------------------------------------------------------------------
# _write_audit + record_trade_outcome
# ----------------------------------------------------------------------
def test_audit_and_record_outcome_failures(engine, tmp_path, monkeypatch, caplog):
    """Covers audit log + backup failures and record_trade_outcome exception."""
    engine.audit_log = str(tmp_path / "audit.csv")
    engine.backup_log = str(tmp_path / "backup.csv")

    caplog.set_level("ERROR")
    monkeypatch.setattr(
        builtins, "open", lambda *a, **k: (_ for _ in ()).throw(Exception("disk full"))
    )
    res1 = engine.process_signal("AAPL", "BUY", 100)
    assert "status" in res1
    assert "audit" in caplog.text.lower()

    # record_trade_outcome failure
    monkeypatch.setattr(
        engine.performance_tracker,
        "record_trade",
        lambda *_: (_ for _ in ()).throw(Exception("rec fail")),
    )
    engine.record_trade_outcome(-100)
    assert "record" in caplog.text.lower()
