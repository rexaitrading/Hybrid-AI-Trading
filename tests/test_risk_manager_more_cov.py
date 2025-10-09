import os

import pytest

from hybrid_ai_trading.risk.risk_manager import RiskConfig, RiskManager


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    os.chdir(tmp_path)
    os.makedirs("logs", exist_ok=True)
    monkeypatch.delenv("FORCE_RISK_HALT", raising=False)
    yield


def test_save_state_exception_branch(monkeypatch, tmp_path):
    calls = {"mk": 0}

    def bad_makedirs(*a, **k):
        calls["mk"] += 1
        raise PermissionError("nope")

    monkeypatch.setattr(os, "makedirs", bad_makedirs)
    # __init__ calls _save_state() internally -> should increment at least once
    rm = RiskManager(RiskConfig(state_path=str(tmp_path / "risk_state.json")))
    assert calls["mk"] >= 1
    # reset and call explicitly once more -> exactly one additional call
    calls["mk"] = 0
    rm._save_state()
    assert calls["mk"] == 1


def test_daily_loss_flag_flip_and_reset(tmp_path):
    rm = RiskManager(RiskConfig(state_path=str(tmp_path / "a.json")))
    rm._state["day_start_equity"] = 10000.0
    rm._state["day_realized_pnl"] = -300.0  # 3% loss -> breach
    ok, reason = rm.allow_trade(notional=1.0, side="BUY", bar_ts=1)
    assert not ok and reason == "DAILY_LOSS" and rm.daily_loss_breached is True
    # recover -> flag should clear; advance past cooldown window
    rm._state["day_realized_pnl"] = 0.0
    next_ts = 1 + (rm.cfg.cooldown_bars * 3600_000 + 1)
    ok2, _ = rm.allow_trade(notional=1.0, side="BUY", bar_ts=next_ts)
    assert ok2 and rm.daily_loss_breached is False


def test_cooldown_expiry_clears_state(tmp_path):
    rm = RiskManager(
        RiskConfig(
            state_path=str(tmp_path / "b.json"),
            cooldown_bars=1,
            max_consecutive_losers=1,
        )
    )
    rm.record_close_pnl(-10.0, bar_ts_ms=1_000_000)  # start cooldown
    ok, _ = rm.allow_trade(notional=1.0, side="BUY", bar_ts=1_000_000 + 1000)
    assert not ok
    ok2, _ = rm.allow_trade(notional=1.0, side="BUY", bar_ts=1_000_000 + 3600_000 + 1)
    assert (
        ok2
        and rm._state.get("halted_until_bar_ts") is None
        and rm._state.get("halted_reason") is None
    )
