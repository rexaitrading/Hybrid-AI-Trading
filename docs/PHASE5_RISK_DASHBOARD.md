# Phase 5 Risk Dashboard

> Combined view of Phase 5 risk sketch config for ORB/VWAP symbols (AAPL, NVDA, SPY, QQQ).

Generated: 2025-11-19 15:07:02

## Summary Table

| Symbol | Has Phase5 Sketch | no_averaging_down | min_add_cushion_bp | daily_loss_cap_pct | daily_loss_cap_notional | symbol_daily_loss_cap_bp | symbol_max_trades_per_day | max_open_positions | Status |
|--------|-------------------|-------------------|--------------------|--------------------|-------------------------|---------------------------|---------------------------|--------------------|--------|
| AAPL | True | True | 3 | -0.02 | -1000 | -50 | 3 | 10 | phase5_sketch_defined |
| NVDA | True | True | 3 | -0.02 | -1000 | -50 | 3 | 10 | phase5_sketch_defined |

## Notes

- **AAPL/NVDA**: phase5_risk_sketch is defined in their ORB/VWAP threshold JSONs and mirrors the Phase5 test harness policy (no averaging down, daily/symbol caps, max_open_positions).
- **SPY/QQQ**: currently no phase5_risk_sketch; EV sweeps show 5 trades with zero pnl and positive costs, so Phase 5 remains disabled for these symbols.
- Engine wiring for Phase 5 is still disabled; this dashboard is for lab/validation only.