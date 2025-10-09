import os, json, tempfile, time
import pytest
from hybrid_ai_trading.risk.risk_manager import RiskManager, RiskConfig

def mk_rm(tmp_path, **kw):
    cfg_defaults = dict(
        day_loss_cap_pct=0.02,
        per_trade_notional_cap=None,
        max_trades_per_day=2,
        max_consecutive_losers=1,
        cooldown_bars=1,
        max_drawdown_pct=0.10,
        fail_closed=True,
        state_path=str(tmp_path/"risk_state.json"),
        base_equity_fallback=10000.0,
    )
    cfg_defaults.update(kw)
    cfg = RiskConfig(**cfg_defaults)
    return RiskManager(cfg)

@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    # ensure clean env & logs per test
    monkeypatch.delenv("FORCE_RISK_HALT", raising=False)
    os.chdir(tmp_path)
    os.makedirs("logs", exist_ok=True)
    yield

def test_load_state_bad_json(tmp_path):
    bad = tmp_path/"risk_state.json"
    bad.write_text("{not json", encoding="utf-8")
    rm = mk_rm(tmp_path)
    # if we reached here, bad json path was handled (load_state except branch)
    assert isinstance(rm._state, dict)

def test_reset_day_if_needed_resets_fields(tmp_path):
    rm = mk_rm(tmp_path)
    rm._state["day"] = "1970-01-01"
    rm._state["day_realized_pnl"] = -123.0
    rm._state["trades_today"] = 9
    rm._state["consecutive_losers"] = 5
    rm._state["halted_until_bar_ts"] = 1
    rm._state["halted_reason"] = "OLD"
    rm.reset_day_if_needed(0)
    s = rm._state
    assert s["trades_today"] == 0 and s["consecutive_losers"] == 0
    assert s["halted_until_bar_ts"] is None and s["halted_reason"] is None

def test_update_equity_peak_and_drawdown(tmp_path):
    rm = mk_rm(tmp_path)
    rm.update_equity(10_000.0)
    rm.update_equity(9_000.0)
    assert rm.current_drawdown is not None and rm.current_drawdown >= 0.09

def test_record_close_pnl_and_cooldown(tmp_path):
    rm = mk_rm(tmp_path, max_consecutive_losers=1, cooldown_bars=1)
    rm.record_close_pnl(-10.0, bar_ts_ms=1_000_000)
    # inside cooldown
    ok, reason = rm.allow_trade(notional=10.0, side="BUY", bar_ts=1_000_000 + 10)
    assert not ok and reason in ("MAX_CONSECUTIVE_LOSERS","COOLDOWN")
    # after cooldown expires (>= 1 hour)
    ok2, _ = rm.allow_trade(notional=10.0, side="BUY", bar_ts=1_000_000 + 3600_000 + 1)
    assert ok2

def test_priority_force_then_daily_loss_then_drawdown(tmp_path, monkeypatch):
    rm = mk_rm(tmp_path)
    # 1) FORCE_RISK_HALT has top priority
    monkeypatch.setenv("FORCE_RISK_HALT", "DEMO")
    ok, reason = rm.allow_trade(notional=1.0, side="BUY", bar_ts=1)
    assert not ok and reason == "DEMO"
    monkeypatch.delenv("FORCE_RISK_HALT", raising=False)
    # 2) DAILY_LOSS before others
    rm._state["day_start_equity"] = 10000.0
    rm._state["day_realized_pnl"] = -500.0  # breach 2%
    ok, reason = rm.allow_trade(notional=1.0, side="BUY", bar_ts=2)
    assert not ok and reason == "DAILY_LOSS"
    # 3) MAX_DRAWDOWN next
    rm._state["day_realized_pnl"] = 0.0
    rm.current_drawdown = 0.2
    ok, reason = rm.allow_trade(notional=1.0, side="BUY", bar_ts=3)
    assert not ok and reason == "MAX_DRAWDOWN"

def test_trades_per_day_and_notional_cap(tmp_path):
    rm = mk_rm(tmp_path, max_trades_per_day=1, per_trade_notional_cap=100.0)
    # within cap first trade
    ok, _ = rm.allow_trade(notional=50.0, side="BUY", bar_ts=1_000_000)
    assert ok
    rm.on_fill(side="BUY", qty=1.0, px=50.0, bar_ts=1_000_000)
    # next same day blocked
    ok2, reason2 = rm.allow_trade(notional=50.0, side="BUY", bar_ts=1_100_000)
    assert not ok2 and reason2 == "TRADES_PER_DAY"
    # notional cap breach
    rm2 = mk_rm(tmp_path, per_trade_notional_cap=100.0)
    ok3, reason3 = rm2.allow_trade(notional=150.0, side="BUY", bar_ts=1_000_000)
    assert not ok3 and reason3 == "NOTIONAL_CAP"

def test_fail_closed_true_and_false(tmp_path, monkeypatch):
    class Explode(RiskManager):
        def reset_day_if_needed(self, bar_ts_ms: int) -> None:
            raise RuntimeError("boom")
    # fail_closed True -> block
    rm1 = Explode(RiskConfig(state_path=str(tmp_path/"a.json"), fail_closed=True))
    ok1, reason1 = rm1.allow_trade(notional=1.0, side="BUY", bar_ts=1)
    assert not ok1 and reason1 == "EXCEPTION"
    # fail_closed False -> allow
    rm2 = Explode(RiskConfig(state_path=str(tmp_path/"b.json"), fail_closed=False))
    ok2, reason2 = rm2.allow_trade(notional=1.0, side="BUY", bar_ts=1)
    assert ok2 and reason2 is None

def test_snapshot_keys(tmp_path):
    rm = mk_rm(tmp_path)
    snap = rm.snapshot()
    for k in ("daily_loss_breached","drawdown","exposure","leverage","day","trades_today","cons_losers","halted_reason"):
        assert k in snap