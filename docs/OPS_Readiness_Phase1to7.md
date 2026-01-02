# Ops Readiness (Phase1–Phase7)

## Daily safety spine (Phase-5)
Run:
- tools\Check-IBGReady.ps1
- tools\Build-BlockGStatusStub.ps1
- tools\Check-BlockGReady.ps1 -Symbol NVDA

## Full readiness audit
Run:
- tools\Audit-Phase1ToPhase7Ready.ps1

## Block-G chokepoint enforcement test
Run:
- python -m pytest -q tests\test_blockg_chokepoint_blocks_live.py

## GateScore freshness policy
- gatescore_fresh_for_session: true when GateScore is fresh for the latest session date in gatescore_pnl_summary.csv
- gatescore_fresh_today: true only when (session date == today_utc) AND fresh_for_session is true
This prevents impossible "fresh today" on weekends/holidays while keeping fail-closed semantics.
