import os
from hybrid_ai_trading.costs import CostInputs, estimate_costs

def test_env_defaults_apply_only_when_inputs_zero(monkeypatch):
    monkeypatch.setenv("HAT_SPREAD_BPS", "1.0")
    monkeypatch.setenv("HAT_COMMISSION_BPS", "2.0")
    monkeypatch.setenv("HAT_SLIPPAGE_BPS", "3.0")

    out = estimate_costs(notional=10000.0, inp=CostInputs())
    assert out.total_bps == 6.0

def test_explicit_inputs_override_env(monkeypatch):
    monkeypatch.setenv("HAT_SPREAD_BPS", "9.0")
    out = estimate_costs(notional=10000.0, inp=CostInputs(spread_bps=1.5, commission_bps=0.0, slippage_bps=0.0))
    assert out.total_bps == 1.5
