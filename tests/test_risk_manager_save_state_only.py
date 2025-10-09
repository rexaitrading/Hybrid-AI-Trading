import os

from hybrid_ai_trading.risk.risk_manager import RiskConfig, RiskManager


def test_save_state_exception_branch(monkeypatch, tmp_path):
    calls = {"mk": 0}

    def bad_makedirs(*a, **k):
        calls["mk"] += 1
        raise PermissionError("nope")

    monkeypatch.setattr(os, "makedirs", bad_makedirs)

    # __init__ may call _save_state() already—should be swallowed
    rm = RiskManager(RiskConfig(state_path=str(tmp_path / "risk_state.json")))
    assert calls["mk"] >= 1  # at least once from __init__

    # Reset counter and invoke _save_state() explicitly once more
    calls["mk"] = 0
    rm._save_state()
    assert calls["mk"] == 1
