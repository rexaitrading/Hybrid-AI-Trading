
### Next 35 days
- Add optional \Get-IBGStatusByPort -Port <int>\ thin wrapper (for completeness) while keeping Paper/Live defaults.
- Add Pester tests for heartbeat JSON schema (portUp/pid/uptimeSec/cpuSec/rssMB/gw/path/lastPing).
- Wire pre-market Slack summary to include both PAPER & LIVE lines atomically.

## Phase-7 (Portfolio Optimizer)
- Stub exists (fail-closed when enabled). Tests enforce safety.

- [2026-01-03 22:01:57] BLOCK-G INSTITUTIONAL LOCK: single-authority PS checker + closed-day semantics + no-bypass + LockPack wired into DailyReadiness.
