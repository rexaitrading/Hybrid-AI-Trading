# tests/test_profitability_guardrails.py
"""
Profitability Guardrails – Hybrid AI Quant Pro v1.0
---------------------------------------------------
Covers:
- ROI vs config target_daily_return
- Sharpe ratio ≥ 0
- Max drawdown within limit
- No NaN values in equity curve
"""

import pytest

from hybrid_ai_trading.trade_engine import TradeEngine


@pytest.fixture
def base_config():
    return {
        "dry_run": True,
        "risk": {
            "equity": 100000,
            "max_daily_loss": -0.03,
            "max_position_risk": 0.01,
            "max_leverage": 5,
            "max_portfolio_exposure": 0.5,
            "target_daily_return": 0.01,  # ✅ 1% target return
        },
        "costs": {"commission_pct": 0.001},
        "features": {"enable_emotional_filter": False},
        "gatescore": {"enabled": False},
        "regime": {"enabled": False},
    }


@pytest.fixture
def trade_engine(base_config):
    return TradeEngine(base_config)


def test_profitability_guardrails(trade_engine):
    # --- Simulate trades ---
    # BUY AAPL at 100 → SELL at 102 = +2% gain
    trade_engine.process_signal("AAPL", "BUY", price=100)
    trade_engine.process_signal("AAPL", "SELL", price=102)

    report = trade_engine.portfolio.report()
    perf = trade_engine.performance_tracker

    # --- ROI Check ---
    roi = (
        report["equity"] - trade_engine.config["risk"]["equity"]
    ) / trade_engine.config["risk"]["equity"]
    target = trade_engine.config["risk"]["target_daily_return"]

    assert (
        roi >= target * 0.5
    ), f"ROI {roi:.2%} below acceptable guardrail (target {target:.2%})"

    # --- Sharpe & Drawdown ---
    sharpe = perf.sharpe_ratio()
    dd = trade_engine.portfolio.get_drawdown()

    assert sharpe >= 0, "Sharpe ratio must be non-negative"
    assert dd <= 0.20, f"Drawdown {dd:.2%} exceeds 20% limit"

    # --- No NaNs ---
    for k, v in report.items():
        if isinstance(v, (float, int)):
            assert v == v, f"{k} has NaN value"

    print(
        f"✅ Guardrails passed | ROI={roi:.2%}, Sharpe={sharpe:.2f}, Drawdown={dd:.2%}"
    )
