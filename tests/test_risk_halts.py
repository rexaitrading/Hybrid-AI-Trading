import os
import tempfile

from hybrid_ai_trading.risk.risk_manager import RiskConfig, RiskManager


def make_rm(tmp):
    cfg = RiskConfig(
        day_loss_cap_pct=0.01,
        per_trade_notional_cap=100.0,
        max_trades_per_day=2,
        max_consecutive_losers=1,
        cooldown_bars=2,
        max_drawdown_pct=0.50,
        state_path=tmp,
        fail_closed=True,
        base_equity_fallback=10000.0,
    )
    return RiskManager(cfg)


def test_per_trade_notional_cap():
    tmp = tempfile.mkstemp(suffix=".json")[1]
    rm = make_rm(tmp)
    ok, reason = rm.allow_trade(notional=500.0, side="BUY", bar_ts=1_000_000)
    assert not ok and reason == "NOTIONAL_CAP"


def test_max_trades_per_day():
    tmp = tempfile.mkstemp(suffix=".json")[1]
    rm = make_rm(tmp)
    ok, _ = rm.allow_trade(notional=50.0, side="BUY", bar_ts=1_000_000)
    assert ok
    rm.on_fill(side="BUY", qty=1.0, px=50.0, bar_ts=1_000_000)
    ok, _ = rm.allow_trade(notional=50.0, side="BUY", bar_ts=1_360_000)
    assert ok
    rm.on_fill(side="BUY", qty=1.0, px=50.0, bar_ts=1_360_000)
    ok, reason = rm.allow_trade(notional=50.0, side="BUY", bar_ts=1_720_000)
    assert not ok and reason == "TRADES_PER_DAY"


def test_cooldown_after_loser():
    tmp = tempfile.mkstemp(suffix=".json")[1]
    rm = make_rm(tmp)
    rm.record_close_pnl(-10.0, bar_ts_ms=1_000_000)
    ok, reason = rm.allow_trade(notional=10.0, side="BUY", bar_ts=1_000_000)
    assert not ok  # cooldown starts at this bar
    ok, reason = rm.allow_trade(
        notional=10.0, side="BUY", bar_ts=1_000_000 + 2 * 3600_000
    )
    assert not ok  # still within 2 bars
    ok, reason = rm.allow_trade(
        notional=10.0, side="BUY", bar_ts=1_000_000 + 3 * 3600_000
    )
    assert ok


def test_daily_loss_cap():
    tmp = tempfile.mkstemp(suffix=".json")[1]
    rm = make_rm(tmp)
    rm.record_close_pnl(-120.0, bar_ts_ms=1_000_000)  # breach: -1% of 10k = -100
    ok, reason = rm.allow_trade(notional=10.0, side="BUY", bar_ts=1_000_001)
    assert not ok and reason == "DAILY_LOSS"


def test_force_halt_env():
    tmp = tempfile.mkstemp(suffix=".json")[1]
    rm = make_rm(tmp)
    os.environ["FORCE_RISK_HALT"] = "TEST_HALT"
    ok, reason = rm.allow_trade(notional=10.0, side="BUY", bar_ts=1_000_000)
    del os.environ["FORCE_RISK_HALT"]
    assert not ok and reason == "TEST_HALT"
