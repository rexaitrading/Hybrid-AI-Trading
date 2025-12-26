import pytest

from hybrid_ai_trading.execution.execution_engine import ExecutionEngine


@pytest.fixture
def cfg(tmp_path):
    return {
        "mode": "paper",
        "audit_log_path": str(tmp_path / "audit.csv"),
        "backup_log_path": str(tmp_path / "backup.csv"),
        "risk": {"equity": 50_000.0, "max_drawdown": 0.2, "kelly": {"win_rate": 0.5, "payoff": 2.0, "fraction": 0.5}},
        # legacy costs (existing tests)
        "costs": {"commission_pct": 0.001, "slippage_pct": 0.001},
    }


def test_cost_gate_enabled_uses_costs_fallback_to_block(monkeypatch, cfg):
    # Enable gate with max below (0.001 + 0.001) = 0.002
    cfg["cost_gate"] = {"enabled": True, "max_total_cost_pct": 0.0015}

    eng = ExecutionEngine(dry_run=True, config=cfg)

    # make risk approve so cost gate is the deciding factor
    monkeypatch.setattr(eng.risk_manager, "approve_trade", lambda *a, **k: True)

    out = eng.place_order("AAPL", "BUY", 1, 100.0)
    assert out["status"] == "rejected"
    assert "cost_gate:" in out["reason"]


def test_cost_gate_overrides_costs(monkeypatch, cfg):
    # Override slippage/commission in cost_gate to be tiny => should pass cost gate
    cfg["cost_gate"] = {"enabled": True, "max_total_cost_pct": 0.0015, "slippage_pct": 0.0, "commission_pct": 0.0}

    eng = ExecutionEngine(dry_run=True, config=cfg)
    monkeypatch.setattr(eng.risk_manager, "approve_trade", lambda *a, **k: True)

    out = eng.place_order("AAPL", "BUY", 1, 100.0)
    assert out["status"] in ("filled", "rejected")  # may reject for other reasons, but not cost_gate
    assert "cost_gate:" not in out.get("reason", "")