import inspect

from hybrid_ai_trading.risk.risk_manager import RiskConfig, RiskManager

cfg = RiskConfig(
    day_loss_cap_pct=0.01,
    per_trade_notional_cap=100.0,
    max_trades_per_day=2,
    max_consecutive_losers=1,
    cooldown_bars=2,
    max_drawdown_pct=0.50,
    state_path="x",
    fail_closed=True,
    base_equity_fallback=10000.0,
)
rm = RiskManager(cfg)  # positional on purpose
print("BOUND:", RiskManager.allow_trade.__name__)
rm.record_close_pnl(-120.0, bar_ts_ms=1_000_000)
print(
    "STATE: pnl_today=",
    getattr(rm, "_pnl_today", None),
    " start_eq=",
    getattr(rm, "starting_equity", None),
    " resolved_eq=",
    rm._resolve_equity(),
    " cfg_like=",
    any(hasattr(v, "day_loss_cap_pct") for v in vars(rm).values()),
)
print("CALL:", rm.allow_trade(notional=10.0, side="BUY", bar_ts=1_000_001))
