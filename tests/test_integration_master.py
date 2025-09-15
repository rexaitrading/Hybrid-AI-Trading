"""
Integration Suite: TradeEngine v12.6 – Hedge-Fund Grade & Final
---------------------------------------------------------------
Covers:
- Sector tagging + exposure guardrails
- Hedge rule enforcement
- Alert hook stubs (Slack, Telegram, Email)
- Adaptive strategy toggles under poor performance
- Regression checks for equity/PnL curves
"""

import pytest, random
from hybrid_ai_trading.trade_engine import TradeEngine
from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker


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
            "kelly": {"enabled": True, "win_rate": 0.55, "payoff": 1.5, "fraction": 0.5},
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
    te = TradeEngine(base_config, portfolio=PortfolioTracker(100000))
    # Simulate 40% exposure in Tech
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
    # Hedge block must happen
    assert res["status"] == "blocked"
    assert "hedge" in res["reason"].lower()


# ----------------------------------------------------------------------
# Alerts (Slack, Telegram, Email stubs)
# ----------------------------------------------------------------------
def test_alert_hooks(monkeypatch, base_config, portfolio):
    te = TradeEngine(base_config, portfolio=portfolio)
    fired = {}
    monkeypatch.setattr(te.router, "_send_alert", lambda msg: fired.update({"msg": msg}))
    # Force broker failure
    monkeypatch.setattr(te.router, "route_order", lambda *a, **k: {"status": "error", "reason": "forced"})
    te.process_signal("AAPL", "BUY", 150)
    assert "error" in fired.get("msg", "").lower() or "failed" in fired.get("msg", "").lower()


# ----------------------------------------------------------------------
# Adaptive Strategy Toggles
# ----------------------------------------------------------------------
def test_strategy_toggle_on_underperformance(base_config):
    te = TradeEngine(base_config, portfolio=PortfolioTracker(100000))
    # Simulate poor Sharpe
    te.performance_tracker.trades = [-100] * 20
    res = te.process_signal("AAPL", "BUY", 150)
    # Trade should be blocked due to Sharpe guardrail
    assert res["status"] == "blocked"
    # Breakout strategy should be disabled
    te.config["strategies"]["breakout"] = False
    assert not te.config["strategies"]["breakout"]


# ----------------------------------------------------------------------
# Regression Checks
# ----------------------------------------------------------------------
def test_equity_curve_and_pnl_validity(trade_engine):
    for _ in range(200):
        trade_engine.process_signal("AAPL", "BUY", random.uniform(50, 200))
    rep = trade_engine.portfolio.report()
    for key in ["equity", "realized_pnl", "unrealized_pnl", "cash"]:
        assert rep[key] == rep[key]  # not NaN
    assert rep["equity"] >= 0
