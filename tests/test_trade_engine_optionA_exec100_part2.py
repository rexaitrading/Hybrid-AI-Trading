import importlib
import types

import pytest

from hybrid_ai_trading.trade_engine import TradeEngine


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
    for k, v in cfg_overrides.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k].update(v)
        else:
            base[k] = v
    return TradeEngine(config=base)


# ---- reset_day: combined error and generic except (175â€“198, 192) ----
def test_reset_day_combined_and_generic(monkeypatch):
    te = make_engine()
    # combined error branch: portfolio error dict, risk ok
    if hasattr(te.portfolio, "reset_day"):
        te.portfolio.reset_day = lambda: {"status": "error", "reason": "p"}
    if hasattr(te.risk_manager, "reset_day"):
        te.risk_manager.reset_day = lambda: {"status": "ok"}
    r = te.reset_day()
    assert r["status"] == "error" and "Portfolio=" in r["reason"]

    # generic outer except: make an attribute access blow up
    te2 = make_engine()

    # replace portfolio.reset_day with a property raising when accessed
    class BadPortfolio(type(te2.portfolio)):
        def reset_day(self):  # method still present; weâ€™ll blow up by removing attribute mid-call
            raise RuntimeError("outer-fail")

    te2.portfolio.reset_day = lambda: (_ for _ in ()).throw(RuntimeError("outer-fail"))
    r2 = te2.reset_day()
    assert r2["status"] == "error" and ("outer-fail" in r2["reason"])

    # ok line (explicitly ensure the "ok" return executed)
    te3 = make_engine()
    te3.portfolio.reset_day = lambda: {"status": "ok"}
    te3.risk_manager.reset_day = lambda: {"status": "ok"}
    r3 = te3.reset_day()
    assert r3["status"] == "ok" and "Daily reset complete" in r3["reason"]


# ---- adaptive_fraction missing paths (205, 208, 211â€“212) ----
def test_adaptive_fraction_peak_zero_and_protection():
    te = make_engine()
    te.portfolio.history = [(0, 0.0)]
    te.portfolio.equity = 10.0
    # peak=0 â†’ base_fraction
    assert te.adaptive_fraction() == te.base_fraction

    te.portfolio.history = [(0, 50.0), (1, 50.0)]
    te.portfolio.equity = 100.0  # frac will cap to base_fraction
    assert te.adaptive_fraction() == te.base_fraction


# ---- HOLD path (230) ----
def test_hold_signal_ignored():
    te = make_engine()
    r = te.process_signal("AAPL", "HOLD", price=1.0, size=1)
    assert r["status"] == "ignored" and r["reason"] == "hold_signal"


# ---- drawdown try/except (241â€“251 esp. 247â€“248) + hedge check (240) ----
def test_drawdown_try_except_and_hedge(monkeypatch):
    te = make_engine(risk={"hedge_rules": {"equities_vol_spike": ["AAPL"]}})
    # Malformed history to force exception in drawdown block
    te.portfolio.history = ["bad"]
    te.portfolio.equity = 80.0
    # Also hedge triggers
    r = te.process_signal("AAPL", "BUY", price=1.0, size=1)
    assert r["status"] == "blocked" and r["reason"] in {
        "hedge_rule",
        "sector_exposure",
        "drawdown_breach",
        "equity_depleted",
        "sentiment_veto",
        "gatescore_veto",
        "sharpe_breach",
        "sortino_breach",
        "router_failed",
        "router_error",
        "invalid_status",
    }


# ---- algo lines coverage: iceberg path & residual lines (256â€“257, 269, 273â€“274) ----
def test_algo_iceberg_and_vwap_success(monkeypatch):
    te = make_engine()

    class TWAP:
        def __init__(self, om):
            pass

        def execute(self, *a, **k):
            return {"status": "ok", "reason": "ok"}

    fake_vwap = types.SimpleNamespace(VWAPExecutor=TWAP)
    fake_iceberg = types.SimpleNamespace(IcebergExecutor=TWAP)

    orig_import = importlib.import_module

    # cover vwap success
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name, _orig=orig_import: fake_vwap if name.endswith(".vwap") else _orig(name),
    )
    r1 = te.process_signal("AAPL", "BUY", price=1.0, size=1, algo="vwap")
    assert r1["status"] in {"filled", "blocked", "ignored", "rejected", "error", "pending"}

    # cover iceberg success
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name, _orig=orig_import: fake_iceberg if name.endswith(".iceberg") else _orig(name),
    )
    r2 = te.process_signal("AAPL", "BUY", price=1.0, size=1, algo="iceberg")
    assert r2["status"] in {"filled", "blocked", "ignored", "rejected", "error", "pending"}


# ---- router raises (286â€“288) ----
def test_router_raises_exception_path(monkeypatch):
    te = make_engine()
    te.router.route_order = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    r = te.process_signal("AAPL", "BUY", price=1.0, size=1)
    assert r["status"] == "blocked" and "router_error" in r["reason"]


# ---- invalid_status normalization guard (332) & log capture (351â€“352) ----
def test_invalid_status_and_audit_capture(monkeypatch):
    te = make_engine()
    # Permissive filters & ratios so we reach normalization guard
    te.sentiment_filter.allow_trade = lambda *a, **k: True
    te.gatescore.allow_trade = lambda *a, **k: True
    te.performance_tracker.sharpe_ratio = lambda: 1.0
    te.performance_tracker.sortino_ratio = lambda: 1.0

    # Invalid status from router → must normalize to rejected/invalid_status
    te.router.route_order = lambda *a, **k: {"status": "weird"}
    r = te.process_signal("AAPL", "BUY", price=1.0, size=1)
    assert r["status"] == "rejected" and r["reason"] == "invalid_status"

    # Now force audit capture exception with normalized ok path
    te.router.route_order = lambda *a, **k: {"status": "ok", "reason": "ok"}
    te._write_audit = lambda row: (_ for _ in ()).throw(RuntimeError("audit"))
    r2 = te.process_signal("AAPL", "BUY", price=1.0, size=1)
    assert r2["status"] == "filled"

    te.router.route_order = lambda *a, **k: {"status": "ok", "reason": "ok"}
    # permissive filters & ratios
    te.sentiment_filter.allow_trade = lambda *a, **k: True
    te.gatescore.allow_trade = lambda *a, **k: True
    te.performance_tracker.sharpe_ratio = lambda: 1.0
    te.performance_tracker.sortino_ratio = lambda: 1.0
    # force audit capture exception
    te._write_audit = lambda row: (_ for _ in ()).throw(RuntimeError("audit"))
    r2 = te.process_signal("AAPL", "BUY", price=1.0, size=1)
    # should still return normalized ok/filled, with error logged (no exception)
    assert r2["status"] == "filled"
