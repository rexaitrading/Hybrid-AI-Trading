
### Next 35 days
- Add optional \Get-IBGStatusByPort -Port <int>\ thin wrapper (for completeness) while keeping Paper/Live defaults.
- Add Pester tests for heartbeat JSON schema (portUp/pid/uptimeSec/cpuSec/rssMB/gw/path/lastPing).
- Wire pre-market Slack summary to include both PAPER & LIVE lines atomically.

## Phase-7 (Portfolio Optimizer)
- Stub exists (fail-closed when enabled). Tests enforce safety.

## Next Perfect Steps (Lock Roadmap)

- Lock-1: CI FinalLock smoke (Run-FinalLock -Mode CI) ✅
- Lock-2: Unify RunContext (ctx authoritative, env fallback only)
- Lock-3: Weekday PreMarket one-tap runs Phase4+Risk tests before FinalLock
- Lock-4: Live guard integration test (deny live orders when Block-G not ready)
- Lock-5: Docs lock (this section)

- Hygiene: clear Dependabot alerts (7 vulns reported 2025-12-28)
