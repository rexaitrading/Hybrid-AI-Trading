import tempfile

from hybrid_ai_trading.risk.risk_manager import RiskConfig, RiskManager


def make_rm(tmp, **kw):
    # Build defaults, then let kw override them (no duplicate kwargs to RiskConfig)
    defaults = dict(
        day_loss_cap_pct=0.01,  # 1%
        per_trade_notional_cap=1000.0,  # allow small notionals
        max_trades_per_day=1,  # easy boundary
        max_consecutive_losers=1,
        cooldown_bars=2,
        max_drawdown_pct=0.05,  # 5%
        state_path=tmp,
        fail_closed=True,
        base_equity_fallback=10_000.0,
    )
    defaults.update(kw)
    cfg = RiskConfig(**defaults)
    return RiskManager(cfg)


def test_reset_day_resets_counters():
    tmp = tempfile.mkstemp(suffix=".json")[1]
    rm = make_rm(tmp)
    rm._state["day"] = "1970-01-01"
    rm._state["day_realized_pnl"] = -123.45
    rm._state["trades_today"] = 9
    rm._state["consecutive_losers"] = 5
    rm._state["halted_until_bar_ts"] = 1
    rm._state["halted_reason"] = "OLD"
    rm._state["last_equity"] = 11111.0
    rm.reset_day_if_needed(bar_ts_ms=0)
    assert rm._state["trades_today"] == 0
    assert rm._state["consecutive_losers"] == 0
    assert rm._state["halted_until_bar_ts"] is None
    assert rm._state["halted_reason"] is None
    assert rm._state["day_start_equity"] == 11111.0


def test_drawdown_halt_priority():
    tmp = tempfile.mkstemp(suffix=".json")[1]
    rm = make_rm(tmp, max_drawdown_pct=0.05)
    rm.update_equity(10_000.0)  # peak
    rm.update_equity(9_000.0)  # 10% DD >= 5% cap
    ok, reason = rm.allow_trade(notional=10.0, side="BUY", bar_ts=1_000_000)
    assert not ok and reason == "MAX_DRAWDOWN"


def test_record_close_positive_resets_losers_and_on_fill_increments():
    tmp = tempfile.mkstemp(suffix=".json")[1]
    rm = make_rm(tmp, max_consecutive_losers=99)
    rm.record_close_pnl(-10.0, bar_ts_ms=1)
    assert rm._state["consecutive_losers"] == 1
    rm.record_close_pnl(+20.0, bar_ts_ms=2)
    assert rm._state["consecutive_losers"] == 0
    assert rm._state["trades_today"] == 0
    rm.on_fill(side="BUY", qty=1, px=10, bar_ts=3)
    assert rm._state["trades_today"] == 1
    assert rm._state["last_trade_bar_ts"] == 3


def test_fail_open_when_fail_closed_false():
    class Boom(RiskManager):
        def reset_day_if_needed(self, _bar_ts_ms: int) -> None:
            raise RuntimeError("boom")

    tmp = tempfile.mkstemp(suffix=".json")[1]
    cfg = RiskConfig(state_path=tmp, fail_closed=False)
    rm = Boom(cfg)
    ok, reason = rm.allow_trade(notional=1.0, side="BUY", bar_ts=1)
    assert ok and reason is None  # fail-open path


def test_daily_loss_flag_resets_when_ok():
    tmp = tempfile.mkstemp(suffix=".json")[1]
    rm = make_rm(tmp, max_consecutive_losers=99)
    rm.record_close_pnl(-10.0, bar_ts_ms=1)  # cap is -100
    ok, reason = rm.allow_trade(notional=10.0, side="BUY", bar_ts=2)
    assert ok and reason is None
    assert rm.daily_loss_breached is False


def test_notional_ok_and_trades_per_day_boundary():
    tmp = tempfile.mkstemp(suffix=".json")[1]
    rm = make_rm(tmp, per_trade_notional_cap=100.0, max_trades_per_day=1)
    ok, reason = rm.allow_trade(notional=50.0, side="BUY", bar_ts=1)
    assert ok
    rm.on_fill(side="BUY", qty=1.0, px=50.0, bar_ts=1)
    ok, reason = rm.allow_trade(notional=50.0, side="BUY", bar_ts=2)
    assert not ok and reason == "TRADES_PER_DAY"


def test_cooldown_expires_and_clears_reason():
    tmp = tempfile.mkstemp(suffix=".json")[1]
    rm = make_rm(tmp, max_consecutive_losers=1, cooldown_bars=2)
    rm.record_close_pnl(-10.0, bar_ts_ms=1_000_000)  # start cooldown
    ok, reason = rm.allow_trade(notional=10.0, side="BUY", bar_ts=1_000_000 + 1 * 3600_000)
    assert not ok
    ok, reason = rm.allow_trade(notional=10.0, side="BUY", bar_ts=1_000_000 + 3 * 3600_000)
    assert ok
    assert rm._state["halted_reason"] is None
