# RunContext Spec (Phase-0)

Single source of truth for the runtime context contract.

## Canonical artifact
- logs/run_context.json (produced by tools/Build-RunContextStub.ps1)
- All consumers must treat missing fields as FAIL-CLOSED.

## Required keys (Phase-0)
- ts_utc (string, ISO-8601)
- as_of_date (string, YYYY-MM-DD)
- phase5_mode (string)  # Phase5-Safety (current)
- phase23_health_ok_today (bool)
- ev_hard_daily_ok_today (bool)
- gatescore_fresh_today (bool)
- nvda_blockg_ready (bool)
- spy_blockg_ready (bool)
- qqq_blockg_ready (bool)

## Semantics
- as_of_date must equal today's trading date
- gatescore_fresh_today must only be true when GateScore is fresh/valid for as_of_date
- *_blockg_ready are per-symbol readiness booleans (fail-closed defaults to false)

## Future Phase-1 (planned, not yet required)
- mode (premarket/paper/live/notion)
- symbol (NVDA/SPY/QQQ/ALL)
- phase4_ok_today (bool)
- blockg_ready (bool)  # consolidated
- paths: repo_root, logs_dir
