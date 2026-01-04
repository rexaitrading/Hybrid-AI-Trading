# CHECKPOINTS

Last updated: 2025-12-22 11:57:15 -08:00

## Latest
- HEAD = c2acdb70

## Notes (Phase5/RunContext lock)
- Block-G chokepoint enforced across brokers + ib_adapter + order_manager
- Contract-only freshness/quality gates enforced for LIVE path
- RunContext JSON reader added (ctx-first intent)

- [2026-01-03 22:01:57] BLOCK-G INSTITUTIONAL LOCK: single-authority PS checker + closed-day semantics + no-bypass + LockPack wired into DailyReadiness.
- [2026-01-03] CHECKPOINT_BLOCKG_LOCK_20260103_220202 — Block-G institutional lock (LockPack green; READY execution allowlist enforced).
- [2026-01-03 22:10:36] BLOCKG_LOCK OK: HEAD=67c29b46 TAG=CHECKPOINT_BLOCKG_LOCK_20260103_220202 LOCKPACK_EXIT=0 READY_EXECUTOR=Arm-NVDA-Live only.
