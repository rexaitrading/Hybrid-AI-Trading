from __future__ import annotations

from hybrid_ai_trading.kelly_sizer import KellySizer
from hybrid_ai_trading.optimizer import allocate_equal_weight


def test_kelly_sizer_returns_numeric_size():
    ks = KellySizer(win_rate=0.55, payoff=1.2, fraction=0.5, regime_factor=1.0)
    size = ks.size_position(equity=10_000.0, price=100.0, risk_veto=False)
    assert isinstance(size, float)
    assert size >= 0.0


def test_equal_weight_alloc_sums_to_one():
    alloc = allocate_equal_weight(["NVDA", "SPY", "QQQ"])
    s = sum(alloc.weights.values())
    assert abs(s - 1.0) < 1e-12