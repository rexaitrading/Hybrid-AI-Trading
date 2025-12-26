from hybrid_ai_trading.execution.cost_gate import evaluate_cost_gate


def test_cost_gate_disabled_allows():
    d = evaluate_cost_gate(cfg={"enabled": False, "max_total_cost_pct": 0.0001})
    assert d.ok is True


def test_cost_gate_enabled_blocks_when_too_high():
    d = evaluate_cost_gate(
        cfg={"enabled": True, "max_total_cost_pct": 0.001, "slippage_pct": 0.001, "commission_pct": 0.001}
    )
    assert d.ok is False
    assert d.reason == "cost_too_high"