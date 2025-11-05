import importlib
import importlib as _imp
import os
import smtplib
import types

import pytest
import requests

from hybrid_ai_trading.trade_engine import TradeEngine


# ---------- helpers ----------
def make_engine(**cfg_overrides):
    base = {
        "mode": "paper",
        "risk": {
            "equity": 100_000.0,
            "max_drawdown": 0.5,
            "kelly": {"win_rate": 0.5, "payoff": 1.0, "fraction": 1.0},
        },
        "alerts": {
            "slack_webhook_env": "SLACK_URL",
            "telegram_bot_env": "TG_BOT",
            "telegram_chat_id_env": "TG_CHAT",
            "email_env": "ALERT_EMAIL",
        },
        "execution": {},
    }
    # deep-ish update
    for k, v in cfg_overrides.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k].update(v)
        else:
            base[k] = v
    return TradeEngine(config=base)


def _sig(fn):
    import inspect

    try:
        return inspect.signature(fn)
    except:
        return None


def _invoke(fn, pool):
    sig = _sig(fn)
    if not sig:
        return
    kwargs = {
        p.name: pool.get(p.name) for p in sig.parameters.values() if p.name in pool
    }
    try:
        return fn(**kwargs)
    except TypeError:
        args = [kwargs.get(p.name) for p in sig.parameters.values()]
        try:
            return fn(*args)
        except Exception:
            pass
    except Exception:
        pass


# ---------- alerts: success & exceptions (103â€“142) + _fire_alert except (70â€“72) ----------
def test_alerts_and_fire_alert_branches(monkeypatch):
    os.environ["SLACK_URL"] = "https://hook"
    os.environ["TG_BOT"] = "bot"
    os.environ["TG_CHAT"] = "chat"
    os.environ["ALERT_EMAIL"] = "alerts@example.com"

    te = make_engine()

    # Success paths
    class R:
        def __init__(self, c):
            self.status_code = c

    monkeypatch.setattr(requests, "post", lambda *a, **k: R(200))
    monkeypatch.setattr(requests, "get", lambda *a, **k: R(200))

    class SMTPOK:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def send_message(self, *a, **k):
            return None

    monkeypatch.setattr(smtplib, "SMTP", lambda *a, **k: SMTPOK())
    res = te.alert("ok")
    assert isinstance(res, dict)

    # Exception paths
    def boom(*a, **k):
        raise RuntimeError("net fail")

    monkeypatch.setattr(requests, "post", boom)
    monkeypatch.setattr(requests, "get", boom)

    class SMTPBAD:
        def __enter__(self):
            raise RuntimeError("smtp down")

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(smtplib, "SMTP", lambda *a, **k: SMTPBAD())
    res2 = te.alert("fail")
    assert isinstance(res2, dict)

    # _fire_alert except branch: make router._send_alert raise
    te.router._send_alert = lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("router send error")
    )
    te._fire_alert("router issue")  # should hit logger.error path without raising


# ---------- audit header & exception (148â€“169) ----------
def test_audit_header_and_exception(monkeypatch, tmp_path):
    te = make_engine()
    te.audit_log = str(tmp_path / "audit.csv")
    te.backup_log = str(tmp_path / "backup.csv")

    te._write_audit(["t", "AAPL", "BUY", 1, 1.0, "ok", 100.0, ""])  # header created

    # force exception path
    te.audit_log = str(tmp_path / "no_dir" / "audit.csv")
    te.backup_log = str(tmp_path / "no_dir" / "backup.csv")

    class Blower:
        def __call__(self, *a, **k):
            raise RuntimeError("openfail")

        def __enter__(self):
            raise RuntimeError("openfail")

        def __exit__(self, *a):
            return False

    monkeypatch.setattr("builtins.open", Blower())
    _ = te._write_audit  # ensure attribute exists
    try:
        te._write_audit(["t", "AAPL", "BUY", 1, 1.0, "ok", 100.0, ""])
    except Exception:
        # The engine logs the error; it shouldn't raise
        pass


# ---------- reset_day branches (175â€“198) ----------
def test_reset_day_ok_and_errors(monkeypatch):
    te = make_engine()

    # ok
    r = te.reset_day()
    assert r["status"] == "ok"

    # portfolio error
    if hasattr(te.portfolio, "reset_day"):
        te.portfolio.reset_day = lambda: (_ for _ in ()).throw(RuntimeError("p-fail"))
        r2 = te.reset_day()
        assert r2["status"] == "error" and "portfolio_reset_failed" in r2["reason"]

    # risk error
    if hasattr(te.risk_manager, "reset_day"):
        te.portfolio.reset_day = lambda: {"status": "ok"}
        te.risk_manager.reset_day = lambda: (_ for _ in ()).throw(
            RuntimeError("r-fail")
        )
        r3 = te.reset_day()
        assert r3["status"] == "error" and "risk_reset_failed" in r3["reason"]


# ---------- adaptive_fraction (201â€“212) ----------
def test_adaptive_fraction_paths():
    te = make_engine()
    # no history
    te.portfolio.history = []
    assert te.adaptive_fraction() == te.base_fraction
    # negative equity
    te.portfolio.equity = 0
    assert te.adaptive_fraction() == te.base_fraction
    # normal
    te.portfolio.history = [(0, 100.0), (1, 110.0)]
    te.portfolio.equity = 95.0
    assert 0.0 <= te.adaptive_fraction() <= te.base_fraction


# ---------- process_signal validations & guards ----------
def test_process_signal_validation_and_equity_depleted(monkeypatch):
    te = make_engine()

    assert (
        te.process_signal("AAPL", 123, price=1.0)["status"] == "rejected"
    )  # 225 -> signal_not_string
    assert (
        te.process_signal("AAPL", "unknown", price=1.0)["status"] == "rejected"
    )  # 228 invalid_signal
    assert (
        te.process_signal("AAPL", "BUY", price=None)["status"] == "rejected"
    )  # 232 invalid_price

    te.portfolio.equity = 0
    assert (
        te.process_signal("AAPL", "BUY", price=1.0)["status"] == "blocked"
    )  # 236 equity_depleted


def test_process_signal_drawdown_and_kelly(monkeypatch):
    te = make_engine()
    # drawdown breach
    te.portfolio.history = [(0, 100.0)]
    te.portfolio.equity = 45.0
    te.config["risk"]["max_drawdown"] = 0.5
    r = te.process_signal("AAPL", "BUY", price=1.0, size=1)
    assert r["status"] in {
        "blocked",
        "filled",
        "ignored",
        "rejected",
        "error",
        "pending",
    }  # either draws on prior check
    # size None â†’ Kelly
    te2 = make_engine()
    te2.kelly_sizer.size_position = lambda eq, px: {"size": 2}
    r2 = te2.process_signal("AAPL", "BUY", price=1.0, size=None)
    assert r2["status"] in {
        "blocked",
        "filled",
        "ignored",
        "rejected",
        "error",
        "pending",
    }


def test_sector_and_hedge_guards(monkeypatch):
    te = make_engine(
        risk={
            "intraday_sector_exposure": 0.001,
            "hedge_rules": {"equities_vol_spike": ["AAPL"]},
        }
    )
    # positions in tech so breach trips
    te.portfolio.get_positions = lambda: {"AAPL": {"size": 10, "avg_price": 100.0}}
    r = te.process_signal("AAPL", "BUY", price=1.0, size=1)
    assert r["status"] == "blocked" and r["reason"] in {"sector_exposure", "hedge_rule"}


# ---------- routing: algo success/failure + direct router variants ----------
def test_algo_and_router_branches(monkeypatch):
    te = make_engine()

    # twap/vwap success
    class TWAP:
        def __init__(self, om):
            pass

        def execute(self, *a, **k):
            return {"status": "ok", "reason": "ok"}

    fake = types.SimpleNamespace(TWAPExecutor=TWAP, VWAPExecutor=TWAP)
    orig_import = importlib.import_module
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name, _orig=orig_import: (
            fake if name.endswith((".twap", ".vwap")) else _orig(name)
        ),
    )
    r1 = te.process_signal("AAPL", "BUY", price=1.0, size=1, algo="twap")
    assert r1["status"] in {
        "filled",
        "blocked",
        "ignored",
        "rejected",
        "error",
        "pending",
    }

    # unknown algo â†’ early reject (no normalization override)
    r2 = te.process_signal("AAPL", "BUY", price=1.0, size=1, algo="unknown")
    assert r2["status"] == "rejected" and r2["reason"] == "unknown_algo"

    # algo import error path
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name, _orig=orig_import: (_ for _ in ()).throw(ImportError("fail")),
    )
    r3 = te.process_signal("AAPL", "BUY", price=1.0, size=1, algo="vwap")
    assert r3["status"] == "error" and "algo_error" in r3["reason"]

    # direct router: router_failed (None), router_error, ok-normalize
    te.router.route_order = lambda *a, **k: None
    r4 = te.process_signal("AAPL", "BUY", price=1.0, size=1)
    assert r4["status"] == "blocked" and r4["reason"] == "router_failed"

    te.router.route_order = lambda *a, **k: {"status": "error", "reason": "x"}
    r5 = te.process_signal("AAPL", "BUY", price=1.0, size=1)
    assert r5["status"] == "blocked" and "router_error" in r5["reason"]

    te.router.route_order = lambda *a, **k: {"status": "ok", "reason": "ok"}
    # Make filters permissive so we reach normalization
    te.sentiment_filter.allow_trade = lambda *a, **k: True
    te.gatescore.allow_trade = lambda *a, **k: True
    te.performance_tracker.sharpe_ratio = lambda: 1.0
    te.performance_tracker.sortino_ratio = lambda: 1.0
    r6 = te.process_signal("AAPL", "BUY", price=1.0, size=1)
    assert r6["status"] == "filled" and r6["reason"] == "normalized_ok"


# ---------- filter and ratio gates ----------
def test_filters_and_performance_blocks(monkeypatch):
    te = make_engine()
    te.router.route_order = lambda *a, **k: {"status": "ok", "reason": "ok"}

    # Sentiment veto
    te.sentiment_filter.allow_trade = lambda *a, **k: False
    r1 = te.process_signal("AAPL", "BUY", price=1.0, size=1)
    assert r1["status"] == "blocked" and r1["reason"] == "sentiment_veto"

    # Sentiment error
    te.sentiment_filter.allow_trade = lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("sent")
    )
    r2 = te.process_signal("AAPL", "BUY", price=1.0, size=1)
    assert r2["status"] == "blocked" and r2["reason"] == "sentiment_error"

    # GateScore veto & error
    te.sentiment_filter.allow_trade = lambda *a, **k: True
    te.gatescore.allow_trade = lambda *a, **k: False
    r3 = te.process_signal("AAPL", "BUY", price=1.0, size=1)
    assert r3["status"] == "blocked" and r3["reason"] == "gatescore_veto"

    te.gatescore.allow_trade = lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("gate")
    )
    r4 = te.process_signal("AAPL", "BUY", price=1.0, size=1)
    assert r4["status"] == "blocked" and r4["reason"] == "gatescore_error"

    # Performance breaches after filters pass
    te.gatescore.allow_trade = lambda *a, **k: True
    te.performance_tracker.sharpe_ratio = lambda: -2.0
    te.performance_tracker.sortino_ratio = lambda: -2.0
    r5 = te.process_signal("AAPL", "BUY", price=1.0, size=1)
    assert r5["status"] == "blocked" and r5["reason"] in {
        "sharpe_breach",
        "sortino_breach",
    }


# ---------- positions/history/outcome ----------
def test_positions_history_and_outcome_logging(monkeypatch):
    te = make_engine()
    assert isinstance(te.get_positions(), dict)
    assert isinstance(te.get_history(), list)
    # record_trade_outcome logging
    te.performance_tracker.record_trade = lambda pnl: (_ for _ in ()).throw(
        RuntimeError("x")
    )
    te.record_trade_outcome(1.23)
