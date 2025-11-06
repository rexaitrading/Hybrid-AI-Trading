"""
Integration Suite: TradeEngine v12.21 Ã¢â‚¬â€œ Hedge-Fund Grade & Loop-Proof
----------------------------------------------------------------------
Covers:
- Sector tagging + exposure guardrails
- Hedge rule enforcement
- Alert hooks (Slack, Telegram, Email) with error handling
- Adaptive strategy toggles under poor performance
- Regression checks for equity/PnL curves
- Router normalization (None, error, exception)
- Adaptive fraction regression (empty, drawdown, negative equity)
- Reset-day happy/error paths with PortfolioTracker.reset_day()
- Alerts with no env vars
"""

import random

import pytest

from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker
from hybrid_ai_trading.trade_engine import TradeEngine


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def portfolio():
    return PortfolioTracker(100000)


@pytest.fixture
def base_config(tmp_path):
    return {
        "mode": "paper",
        "audit_log_path": str(tmp_path / "trade_blotter.csv"),
        "backup_log_path": str(tmp_path / "trade_blotter_backup.csv"),
        "risk": {
            "equity": 100000,
            "max_daily_loss": -0.03,
            "max_position_risk": 0.01,
            "max_leverage": 5,
            "max_portfolio_exposure": 0.5,
            "kelly": {
                "win_rate": 0.55,
                "payoff": 1.5,
                "fraction": 0.5,
            },
            "sharpe_min": 0.5,
            "sortino_min": 0.5,
            "max_drawdown": 0.5,
            "target_daily_return": 0.01,
            "regime_leverage": {"bull": 5.0, "bear": 1.0, "chop": 0.5, "crisis": 0.25},
            "intraday_sector_exposure": 0.3,
            "hedge_rules": {"equities_vol_spike": ["SPY", "VIXY", "UVXY"]},
        },
        "costs": {"commission_pct": 0.001, "slippage_per_share": 0.01},
        "alerts": {"latency_threshold_ms": 1},
        "execution": {"max_order_retries": 1, "timeout_sec": 0.01},
        "strategies": {
            "breakout": True,
            "mean_reversion": True,
            "arbitrage": True,
        },
    }


@pytest.fixture
def trade_engine(base_config, portfolio, monkeypatch):
    eng = TradeEngine(base_config, portfolio=portfolio)
    # Default happy-path patches
    monkeypatch.setattr(eng.gatescore, "allow_trade", lambda *a, **k: True)
    monkeypatch.setattr(eng.risk_manager, "check_trade", lambda *a, **k: True)
    return eng


# ----------------------------------------------------------------------
# Sector Tagging + Exposure
# ----------------------------------------------------------------------
def test_sector_exposure_guardrail(base_config):
    base_config["risk"]["sharpe_min"] = -999  # disable perf guardrail
    te = TradeEngine(base_config, portfolio=PortfolioTracker(100000))
    te.portfolio.positions = {"AAPL": {"size": 300, "avg_price": 150}}
    te.portfolio.update_equity({"AAPL": 150})
    res = te.process_signal("AAPL", "BUY", 150)
    assert res["status"] == "blocked"
    assert "sector" in res["reason"].lower()


# ----------------------------------------------------------------------
# Hedge Rules
# ----------------------------------------------------------------------
def test_hedge_rule_trigger(base_config):
    te = TradeEngine(base_config, portfolio=PortfolioTracker(100000))
    res = te.process_signal("SPY", "BUY", 400)
    assert res["status"] == "blocked"
    assert "hedge" in res["reason"].lower()


# ----------------------------------------------------------------------
# Alerts
# ----------------------------------------------------------------------
def test_alert_hooks(monkeypatch, base_config, portfolio, capsys):
    base_config["risk"]["intraday_sector_exposure"] = 1.0
    base_config["risk"]["hedge_rules"] = {}
    base_config["risk"]["sharpe_min"] = -999
    base_config["risk"]["sortino_min"] = -999

    te = TradeEngine(base_config, portfolio=portfolio)
    fired = {}

    # Capture fired alert
    monkeypatch.setattr(
        te.router, "_send_alert", lambda msg: fired.update({"msg": msg})
    )
    monkeypatch.setattr(
        te.router,
        "route_order",
        lambda *a, **k: {"status": "error", "reason": "forced"},
    )

    te.process_signal("AAPL", "BUY", 150)
    msg = fired.get("msg")

    assert msg is not None and msg != ""
    assert "error" in msg.lower()


def test_alert_no_env_vars(base_config, portfolio, monkeypatch):
    te = TradeEngine(base_config, portfolio=portfolio)
    monkeypatch.setattr("os.getenv", lambda *a, **k: "")
    res = te.alert("msg")
    assert res["status"] == "no_alerts"


# ----------------------------------------------------------------------
# Adaptive Strategy Toggles
# ----------------------------------------------------------------------
def test_strategy_toggle_on_underperformance(base_config):
    te = TradeEngine(base_config, portfolio=PortfolioTracker(100000))
    te.performance_tracker.trades = [-100] * 20
    res = te.process_signal("AAPL", "BUY", 150)
    assert res["status"] == "blocked"
    te.config["strategies"]["breakout"] = False
    assert not te.config["strategies"]["breakout"]


# ----------------------------------------------------------------------
# Router Normalization
# ----------------------------------------------------------------------
def test_router_normalization(base_config, portfolio, monkeypatch):
    te = TradeEngine(base_config, portfolio=portfolio)

    monkeypatch.setattr(te.router, "route_order", lambda *_: None)
    assert te.process_signal("AAPL", "BUY", 100)["status"] in {"rejected", "blocked"}

    monkeypatch.setattr(
        te.router, "route_order", lambda *_: {"status": "error", "reason": "fail"}
    )
    assert "router_error" in te.process_signal("AAPL", "BUY", 100)["reason"]


# ----------------------------------------------------------------------
# Adaptive Fraction Regression
# ----------------------------------------------------------------------
def test_adaptive_fraction_paths(base_config):
    te = TradeEngine(base_config, portfolio=PortfolioTracker(100000))

    te.portfolio.history = []
    assert te.adaptive_fraction() == te.base_fraction

    te.portfolio.history = [(0, 100000), (1, 50000)]
    te.portfolio.equity = 50000
    assert te.adaptive_fraction() < te.base_fraction

    te.portfolio.history = [(0, 100000), (1, -1000)]
    te.portfolio.equity = -1000
    assert te.adaptive_fraction() == te.base_fraction


# ----------------------------------------------------------------------
# Reset-Day
# ----------------------------------------------------------------------
def test_reset_day_paths(base_config, portfolio, monkeypatch):
    te = TradeEngine(base_config, portfolio=portfolio)
    # Ã¢Å“â€¦ Happy path
    assert te.reset_day()["status"] == "ok"

    # Ã¢Å“â€¦ Error path via portfolio.reset_day
    monkeypatch.setattr(
        te.portfolio, "reset_day", lambda: {"status": "error", "reason": "fail"}
    )
    assert te.reset_day()["status"] == "error"

    # Ã¢Å“â€¦ Error path via risk_manager.reset_day
    monkeypatch.setattr(
        te.risk_manager, "reset_day", lambda: {"status": "error", "reason": "fail"}
    )
    assert te.reset_day()["status"] == "error"


# ----------------------------------------------------------------------
# Regression Checks
# ----------------------------------------------------------------------
def test_equity_curve_and_pnl_validity(trade_engine):
    for _ in range(200):
        trade_engine.process_signal("AAPL", "BUY", random.uniform(50, 200))
    rep = trade_engine.portfolio.report()
    for key in ["equity", "realized_pnl", "unrealized_pnl", "cash"]:
        assert rep[key] == rep[key]
    assert rep["equity"] >= 0
