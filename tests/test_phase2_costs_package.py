from __future__ import annotations

from hybrid_ai_trading.cost import CostInputs, estimate_costs

def test_costs_reexport_smoke():
    r = estimate_costs(notional=100000.0, inp=CostInputs(spread_bps=1.0, commission_bps=2.0, slippage_bps=3.0))
    assert round(r.total_bps, 6) == 6.0
    assert round(r.total_cost, 6) == 60.0
