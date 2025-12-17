from __future__ import annotations

from hybrid_ai_trading.costs import CostInputs, estimate_costs
from hybrid_ai_trading.microstructure import compute_microstructure_features


def test_costs_deterministic():
    est = estimate_costs(notional=10_000.0, inp=CostInputs(spread_bps=1.0, commission_bps=2.0, slippage_bps=3.0))
    assert est.total_bps == 6.0
    assert est.total_cost > 0.0
    assert est.effective_notional < 10_000.0


def test_microstructure_package_reexport_works():
    feats = compute_microstructure_features(closes=[100.0, 101.0], volumes=[10.0, 20.0])
    assert feats.volume_sum == 30.0