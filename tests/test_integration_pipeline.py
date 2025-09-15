"""
Integration Pipeline Tests (Hybrid AI Quant Pro v1.6 – Stress + Emotion, AAA Polished)
-------------------------------------------------------------------------------------
Covers:
- TradeEngine BUY flow → portfolio & performance tracker updated
- TradeEngine SELL flow → closes or reduces position (Kelly partial close safe)
- RiskManager veto blocks trade (forced always-block config)
- KellySizer adapts fraction with drawdown
- Input validation: non-string signal, HOLD, bad price
- GateScore veto and exception branches
- Sentiment veto and exception branches
- Stress test: 200 random trades
- Emotional test: sentiment filter blocking bad headlines
"""

import pytest, random
from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker
from hybrid_ai_trading.execution.order_manager import OrderManager
from hybrid_ai_trading.risk.risk_manager import RiskManager
from hybrid_ai_trading.trade_engine import TradeEngine


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------
@pytest.fixture
def base_config():
    return {
        "dry_run": True,
        "use_paper_simulator": False,
        "risk": {
            "equity": 100000,
            "max_daily_loss": -0.03,
            "max_position_risk": 0.01,
            "max_leverage": 5,
            "max_portfolio_exposure": 0.5,
            "kelly": {"enabled": True, "win_rate": 0.55, "payoff": 1.5, "fraction": 0.5},
        },
        "costs": {"commission_pct": 0.001, "slippage_per_share": 0.01},
        "features": {"enable_emotional_filter": True},
        "sentiment": {"threshold": 0.8, "neutral_zone": 0.2, "bias": "none", "model": "vader"},
        "gatescore": {"enabled": True, "threshold": 0.85, "adaptive": True},
        "regime": {"enabled": False},
    }


@pytest.fixture
def trade_engine(base_config, monkeypatch):
    eng = TradeEngine(base_config)
    # Default happy-path patches
    monkeypatch.setattr(eng.gatescore, "allow_trade", lambda *a, **k: True)
    monkeypatch.setattr(eng.sentiment_filter, "allow_trade", lambda *a, **k: True)
    monkeypatch.setattr(eng.risk_manager, "check_trade", lambda *a, **k: True)
    return eng


# -------------------------------------------------------------------
# Core Trade Flows
# -------------------------------------------------------------------
def test_buy_flow_updates_portfolio_and_perf(trade_engine):
    result = trade_engine.process_signal("AAPL", "BUY", 150.0)
    assert result["status"] == "filled"
    assert "AAPL" in trade_engine.get_positions()
    assert trade_engine.performance_tracker.trades[-1] > 0


def test_sell_flow_closes_or_reduces_position(trade_engine):
    """End-to-end SELL flow reduces or closes position safely."""
    trade_engine.process_signal("AAPL", "BUY", 150.0)
    result = trade_engine.process_signal("AAPL", "SELL", 155.0)

    assert result["status"] in {"filled", "blocked"}
    if result["status"] == "filled":
        pos = trade_engine.get_positions().get("AAPL", {"size": 0})["size"]
        # ✅ Either fully closed OR reduced position (Kelly partial close safe)
        assert pos <= 0 or pos < 83


def test_risk_manager_veto_blocks_trade():
    """Force RiskManager always veto → order blocked, no portfolio update."""
    pt = PortfolioTracker(100000)
    rm = RiskManager(
        daily_loss_limit=0.0,
        trade_loss_limit=0.0,
        max_leverage=0.0,
        equity=100000,
        max_portfolio_exposure=0.0,
        portfolio=pt,
    )
    om = OrderManager(risk_manager=rm, portfolio=pt, dry_run=True)
    result = om.place_order("TSLA", "BUY", 10, 100)
    assert result["status"] == "blocked"
    assert "Risk" in result["reason"] or "veto" in result["reason"]


def test_kelly_sizer_scales_with_drawdown(base_config):
    te = TradeEngine(base_config)
    f1 = te.adaptive_fraction()
    te.portfolio.history = [(0, 100000), (1, 75000)]
    te.portfolio.equity = 75000
    f2 = te.adaptive_fraction()
    assert f2 < f1


# -------------------------------------------------------------------
# Input Validation
# -------------------------------------------------------------------
def test_invalid_signal_and_price(trade_engine):
    res = trade_engine.process_signal("AAPL", 123, 150.0)
    assert res["status"] == "rejected"
    assert "Signal not string" in res["reason"]

    res = trade_engine.process_signal("AAPL", "hold", 150.0)
    assert res["status"] == "ignored"

    res = trade_engine.process_signal("AAPL", "BUY", -1.0)
    assert res["status"] == "rejected"
    assert "Invalid price" in res["reason"]


# -------------------------------------------------------------------
# GateScore & Sentiment Branches
# -------------------------------------------------------------------
def test_gatescore_veto_blocks(trade_engine, monkeypatch):
    monkeypatch.setattr(trade_engine.gatescore, "allow_trade", lambda *a, **k: False)
    result = trade_engine.process_signal("AAPL", "BUY", 150.0)
    assert result["status"] == "blocked"
    assert "GateScore" in result["reason"]


def test_gatescore_exception_blocks(trade_engine, monkeypatch):
    def boom(*a, **k): raise RuntimeError("fail")
    monkeypatch.setattr(trade_engine.gatescore, "allow_trade", boom)
    result = trade_engine.process_signal("AAPL", "BUY", 150.0)
    assert result["status"] == "blocked"
    assert "GateScore" in result["reason"]


def test_sentiment_veto_blocks(trade_engine, monkeypatch):
    monkeypatch.setattr(trade_engine.sentiment_filter, "allow_trade", lambda *a, **k: False)
    result = trade_engine.process_signal("AAPL", "BUY", 150.0)
    assert result["status"] == "blocked"
    assert "Sentiment" in result["reason"]


def test_sentiment_exception_blocks(trade_engine, monkeypatch):
    def bad_score(*a, **k): raise Exception("boom")
    monkeypatch.setattr(trade_engine.sentiment_filter, "allow_trade", bad_score)
    result = trade_engine.process_signal("AAPL", "BUY", 150.0)
    assert result["status"] == "blocked"
    assert "Sentiment" in result["reason"]


# -------------------------------------------------------------------
# Stress & Emotional Tests
# -------------------------------------------------------------------
def test_stress_random_trades(trade_engine):
    """Run 200 random trades to check stability and PnL tracking."""
    symbols = ["AAPL", "TSLA", "MSFT", "AMZN", "META"]
    for _ in range(200):
        sym = random.choice(symbols)
        side = random.choice(["BUY", "SELL"])
        price = random.uniform(50, 500)
        res = trade_engine.process_signal(sym, side, price)
        assert res["status"] in {"filled", "blocked", "ignored", "rejected"}
    assert trade_engine.get_equity() >= 0


def test_emotional_sentiment_blocks(base_config, monkeypatch):
    """Simulate negative headline → SentimentFilter vetoes trade."""
    base_config["features"]["enable_emotional_filter"] = True
    base_config["gatescore"]["enabled"] = False   # ✅ Disable GateScore so Sentiment runs
    te = TradeEngine(base_config)
    monkeypatch.setattr(te.sentiment_filter, "allow_trade", lambda *a, **k: False)
    res = te.process_signal("AAPL", "BUY", 150.0)
    assert res["status"] == "blocked"
    assert "Sentiment" in res["reason"]
