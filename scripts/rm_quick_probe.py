from hybrid_ai_trading.risk.risk_manager import RiskConfig, RiskManager

rm = RiskManager(
    RiskConfig(
        day_loss_cap_pct=0.02,
        max_drawdown_pct=0.08,
        max_trades_per_day=2,
        max_consecutive_losers=1,
        cooldown_bars=1,
    )
)
now = 1_700_000_000_000


def clear_halts():
    rm._state["halted_until_bar_ts"] = None
    rm._state["halted_reason"] = None


def clear_daily():
    rm._state["day_realized_pnl"] = 0.0


def clear_drawdown():
    # reset peak & equity so drawdown=0
    rm._state["rolling_peak_equity"] = 100.0
    rm.update_equity(100.0)


def clear_trades():
    rm._state["trades_today"] = 0


def header(s):
    print("\n=== " + s + " ===")


# 0) Baseline allow
header("baseline allow")
clear_halts()
clear_daily()
clear_drawdown()
clear_trades()
ok, reason = rm.allow_trade(notional=1000, side="BUY", bar_ts=now)
print("allow:", ok, reason)

# 1) Daily loss breach
header("daily loss cap")
clear_halts()
clear_drawdown()
clear_trades()
rm._state["day_realized_pnl"] = -999999.0
ok, reason = rm.allow_trade(notional=100, side="BUY", bar_ts=now + 1)
print("after big loss:", ok, reason)
clear_daily()  # reset for next tests

# 2) Max drawdown
header("max drawdown")
clear_halts()
clear_daily()
clear_trades()
rm._state["rolling_peak_equity"] = 100.0
rm.update_equity(92.0)  # 8% dd
ok, reason = rm.allow_trade(notional=100, side="BUY", bar_ts=now + 2)
print("after drawdown:", ok, reason)
clear_drawdown()  # remove dd for subsequent tests

# 3) Cooldown after losers
header("cooldown after losers")
clear_halts()
clear_daily()
clear_trades()
rm._state["consecutive_losers"] = 1
rm._state["halted_until_bar_ts"] = now + 3
rm._state["halted_reason"] = "MAX_CONSECUTIVE_LOSERS"
ok, reason = rm.allow_trade(notional=100, side="BUY", bar_ts=now + 3)  # inside window
print("cooldown active:", ok, reason)
# advance beyond cooldown: 1 bar = 3_600_000 ms
ok, reason = rm.allow_trade(
    notional=100, side="BUY", bar_ts=now + 3 + rm.cfg.cooldown_bars * 3_600_000 + 1
)
print("after cooldown:", ok, reason)

# 4) Trades/day limit
header("max trades per day")
clear_halts()
clear_daily()
clear_drawdown()
rm._state["trades_today"] = rm.cfg.max_trades_per_day
ok, reason = rm.allow_trade(notional=100, side="BUY", bar_ts=now + 4)
print("max trades/day:", ok, reason)
clear_trades()

# 5) Notional cap
header("per-trade notional cap")
clear_halts()
clear_daily()
clear_drawdown()
clear_trades()
rm.cfg.per_trade_notional_cap = 50.0
ok, reason = rm.allow_trade(notional=70.0, side="BUY", bar_ts=now + 5)
print("notional cap:", ok, reason)

print("\nfinal snapshot:", rm.snapshot())
