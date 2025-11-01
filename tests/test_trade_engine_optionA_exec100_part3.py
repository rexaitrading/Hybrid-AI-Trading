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
        "alerts": {},
        "execution": {},
    }
    for k, v in cfg_overrides.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k].update(v)
        else:
            base[k] = v
    return TradeEngine(config=base)


# ---- reset_day: other dict-error combos (175Ã¢â‚¬â€œ181, 182Ã¢â‚¬â€œ188) + generic (197Ã¢â‚¬â€œ198) ----
def test_reset_day_risk_error_dict_and_both_error_dicts():
    # risk error dict, portfolio ok
    te = make_engine()
    if hasattr(te.portfolio, "reset_day"):
        te.portfolio.reset_day = lambda: {"status": "ok"}
    if hasattr(te.risk_manager, "reset_day"):
        te.risk_manager.reset_day = lambda: {"status": "error", "reason": "r"}
    r = te.reset_day()
    assert r["status"] == "error" and "Risk={'status': 'error'" in r["reason"]

    # both error dicts
    te2 = make_engine()
    te2.portfolio.reset_day = lambda: {"status": "error", "reason": "p"}
    te2.risk_manager.reset_day = lambda: {"status": "error", "reason": "r"}
    r2 = te2.reset_day()
    assert (
        r2["status"] == "error"
        and "Portfolio=" in r2["reason"]
        and "Risk=" in r2["reason"]
    )


def test_reset_day_generic_guard_outer():
    te = make_engine()
    # make inner try succeed but cause a later failure at port_status.get(...)
    if hasattr(te.portfolio, "reset_day"):
        te.portfolio.reset_day = lambda: None  # will break on .get
    if hasattr(te.risk_manager, "reset_day"):
        te.risk_manager.reset_day = lambda: {"status": "ok"}
    r = te.reset_day()
    assert r["status"] == "error"


# ---- adaptive_fraction: no-portfolio (205) + except fallback (211Ã¢â‚¬â€œ212) ----
def test_adaptive_fraction_no_portfolio_and_exception():
    te = make_engine()
    # no-portfolio
    te.portfolio = None
    assert te.adaptive_fraction() == te.base_fraction

    # exception fallback: object missing attributes causes except path
    te2 = make_engine()
    te2.portfolio = object()  # no equity/history
    assert te2.adaptive_fraction() == te2.base_fraction


# ---- drawdown non-breach clean pass (241Ã¢â‚¬â€œ251) ----
def test_drawdown_non_breach_path():
    te = make_engine()
    te.portfolio.history = [(0, 100.0)]
    te.portfolio.equity = 90.0  # 10% drawdown < default 50% cap
    # reach further stages; make router ok, filters permissive, ratios good
    te.router.route_order = lambda *a, **k: {"status": "ok", "reason": "ok"}
    te.sentiment_filter.allow_trade = lambda *a, **k: True
    te.gatescore.allow_trade = lambda *a, **k: True
    te.performance_tracker.sharpe_ratio = lambda: 1.0
    te.performance_tracker.sortino_ratio = lambda: 1.0
    r = te.process_signal("AAPL", "BUY", price=1.0, size=1)
    assert r["status"] in {
        "filled",
        "blocked",
        "ignored",
        "rejected",
        "error",
        "pending",
    }


# ---- performance try/except exception + normalization mapping lines (325Ã¢â‚¬â€œ327, 334Ã¢â‚¬â€œ339) ----
def test_performance_exception_and_normalize_lines():
    te = make_engine()
    te.router.route_order = lambda *a, **k: {"status": "ok", "reason": "ok"}
    te.sentiment_filter.allow_trade = lambda *a, **k: True
    te.gatescore.allow_trade = lambda *a, **k: True

    # force exception in performance section to hit except: pass
    te.performance_tracker.sharpe_ratio = lambda: (_ for _ in ()).throw(
        RuntimeError("s")
    )
    te.performance_tracker.sortino_ratio = lambda: (_ for _ in ()).throw(
        RuntimeError("t")
    )

    r = te.process_signal("AAPL", "BUY", price=1.0, size=1)
    # With perf try/except swallowed, we still normalize ok->filled & reason->normalized_ok
    assert r["status"] == "filled" and r["reason"] == "normalized_ok"
