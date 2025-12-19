import pytest

from hybrid_ai_trading.execution.cost_gate import evaluate_cost_gate, estimate_total_cost_pct


def test_latency_penalty_affects_total_cost():
    cfg = {"enabled": True, "max_total_cost_pct": 0.002, "slippage_pct": 0.0, "commission_pct": 0.0,
           "latency_ms": 50, "latency_penalty_per_ms": 0.0001}
    # 50 * 0.0001 = 0.005 => should exceed max
    d = evaluate_cost_gate(cfg=cfg)
    assert d.ok is False
    assert d.reason == "cost_too_high"


def test_latency_disabled_by_default_in_gate():
    # If enabled=False, always ok regardless of latency fields
    cfg = {"enabled": False, "latency_ms": 10_000, "latency_penalty_per_ms": 1.0}
    d = evaluate_cost_gate(cfg=cfg)
    assert d.ok is True