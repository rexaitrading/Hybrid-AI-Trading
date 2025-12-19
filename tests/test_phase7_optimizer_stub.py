import pytest

from hybrid_ai_trading.optimizer import OptimizerNotReady, optimize_portfolio


def test_optimizer_disabled_is_safe():
    out = optimize_portfolio(inputs={"symbols": ["AAPL"]}, cfg={"enabled": False})
    assert out.ok is False
    assert out.reason == "optimizer_disabled"


def test_optimizer_enabled_fail_closed():
    with pytest.raises(OptimizerNotReady):
        optimize_portfolio(inputs={"symbols": ["AAPL"]}, cfg={"enabled": True})