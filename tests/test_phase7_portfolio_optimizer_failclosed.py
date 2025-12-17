from __future__ import annotations

from hybrid_ai_trading.portfolio_optimizer import PortfolioOptimizer
from hybrid_ai_trading.portfolio_optimizer.constraints import PortfolioConstraints


def test_phase7_fail_closed_on_empty_scores():
    opt = PortfolioOptimizer(fail_closed=True)
    res = opt.optimize(strategy_scores={})
    assert res.ok is False
    assert res.weights == {}
    assert "no_strategy_scores" in res.reasons


def test_phase7_equal_weight_basic_with_relaxed_constraints():
    # Equal-weight(3) => 1/3 each; must allow >= 0.3333
    c = PortfolioConstraints(max_gross_exposure=1.0, max_single_name=0.34)
    opt = PortfolioOptimizer(constraints=c, fail_closed=True)

    res = opt.optimize(strategy_scores={"NVDA": 1.0, "SPY": 0.5, "QQQ": 0.2})
    assert res.ok is True
    assert isinstance(res.weights, dict)
    assert abs(sum(res.weights.values()) - 1.0) < 1e-12
    assert all(v >= 0.0 for v in res.weights.values())


def test_phase7_fail_closed_when_single_name_cap_blocks_equal_weight():
    # Equal-weight(3) violates max_single_name=0.25 -> must fail closed and return {}
    c = PortfolioConstraints(max_gross_exposure=1.0, max_single_name=0.25)
    opt = PortfolioOptimizer(constraints=c, fail_closed=True)

    res = opt.optimize(strategy_scores={"NVDA": 1.0, "SPY": 0.5, "QQQ": 0.2})
    assert res.ok is False
    assert res.weights == {}
    assert any(r.startswith("single_name_exceeds_limit:") for r in res.reasons)