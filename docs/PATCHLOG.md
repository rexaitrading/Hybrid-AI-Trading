---
## 2026-01-11 - Block-G: PS Semantic Owner End-to-End (squash)

Commit: 9abdcc36

What changed:
- IB order chokepoint: LIVE gates use PowerShell Check-BlockGReady as single semantic owner.
- Checker: fail-closed on contract_semantics_level != FULL_LIVE_ELIGIBLE.
- Builder: FULL contract now emits build_mode=FULL and contract_semantics_level=FULL_LIVE_ELIGIBLE.
- Master-Launch: no longer forces FAST builder (FULL semantics required for readiness).
- Phase5 guard: LIVE uses PowerShell checker (no Python recompute).

Validation (2026-01-11 Sunday):
- Build-BlockGStatusStub OK (FULL contract emitted).
- Check-BlockGReady denies on market_closed_today=true (expected).
- Python compile OK.
- Phase5 paper smoke OK.

---
---
## 2026-01-11 - Intel/Tools Re-entry (stash@{1}) - Split commits

Goal: Re-apply stashed intel/tools work in a controlled way; keep scheduled/crypto task scripts isolated.

Commit 1: fix(intel): collectors harden + provider audit wiring (f0db591c)
- collectors: collect_cli / collect_news_multi / collect_youtube_rss
- ops: quiet provider spam; separate YouTube hours-back env

Commit 2: chore(tools): intel pipeline + gatescore summary scripts harden (626f33d2)
- tools scripts updated for scheduled intel pipeline + GateScore summaries

Validation:
- git status clean after commits
- UTF-8 no-BOM + LF enforced on touched files (fixed missing newline in collect_cli.py)

---
---
## 2026-01-11 06:35 UTC - Crypto Asia Paper Ops: Calm Validation Mode (Institutional)

Goal: Deterministic, low-whipsaw crypto paper-sim aligned with Phase-1->Phase-7 standards (fail-closed, anti-churn, reproducible).

What was hardened
- Warmup isolation (dry-run only)
  - Warmup computes prices -> signals -> gates -> risk but never fills.
  - dry_run_no_trade events logged for audit clarity.
  - dry-run executes before allow gate (no side effects).
- Main tick integrity (fills allowed)
  - Main tick is not dry-run; fills only occur when gates pass.
- Anti-churn and risk realism
  - Per-symbol cooldown
  - min_hold_sec enforced (min_hold_sec_block)
  - no pyramiding (already_long_no_add)
  - per-symbol max trades per hour
- Calm price dynamics (demo feed)
  - Smooth mean-reverting walk
  - BtcStepMax=10, EthStepMax=0.8, MeanRevert=0.15
- Signal stability
  - lookback=6, thr=0.00030

Files touched
- tools/Run-CryptoPaperOps-Asia.ps1
- tools/Write-CryptoPriceSnapshot-Demo.ps1
- src/hybrid_ai_trading/runners/crypto_paper_sim.py

Validation gates
- PowerShell parse: OK
- Python compile: OK
- Scheduled task: HAT_Crypto_PaperOps_Asia runs clean (exit=0)
- Logs: warmup shows dry_run_no_trade; main tick can produce fills

Status: LIVE (paper) in calm validation mode. No further wiring required.
---

# PATCHLOG  2025-11-07 00:20:44 -08:00

- IBG module (`C:\IBC\IBGTools.psm1`):
  - Added **paramless** helpers: `Get-IBGStatusPaper`, `Get-IBGStatusLive` for binder-proof fixed ports (4002/4001).
  - Kept legacy `Get-IBGStatus -Port` and supporting functions; explicit **Export-ModuleMember** authoritative line.
  - Introduced `Set-IBCDirectory` (approved verb) and ensured UTF-8 **no BOM** throughout.

- Heartbeat pipeline:
  - Shape-safe accessor `Get-SafeProp` pattern in wrappers to avoid property errors when LIVE is down.
  - Confirmed writes: `C:\IBC\status\ibg_status.json`, `ibg_live_status.json`.

- Runspace hardening:
  - Purged stray typed `[switch]$live` from Local/Script/Global scopes before assignments.
  - Avoided ambiguous variable names in wrappers (`$liveStatus/$paperStatus`).

- Scheduler:
  - Safe TaskName (no colon), safe `-Argument` quoting, S4U + Highest at 06:55 PT.

- Single source of truth:
  - All watchers/wrappers import `C:\IBC\IBGTools.psm1`. Legacy Extras/Loader may be retired.# PATCHLOG (surgical changes)

## 20251103_190435  RiskManager: DAILY_LOSS gate hardened
**Why:** Stabilize daily-loss flag and parser-safe block

**Files:** src\hybrid_ai_trading\risk\risk_manager.py
**Logs:** ./logs/20251103_190435/
**Backups:** ./.backup/*.20251103_190435.bak

**Tests:** python -m pytest -q -k risk_manager_more_cov

**Summary (tail):**
E       ^^^^^^^
E   SyntaxError: expected 'except' or 'finally' block
============================== warnings summary ===============================
src\hybrid_ai_trading\algos\__init__.py:24
  C:\Dev\HybridAITrading\src\hybrid_ai_trading\algos\__init__.py:24: Warning: deprecated: hybrid_ai_trading.algos  use concrete algo modules directly
    _emit()

src\hybrid_ai_trading\execution\algos\__init__.py:17
  C:\Dev\HybridAITrading\src\hybrid_ai_trading\execution\algos\__init__.py:17: Warning: deprecated: hybrid_ai_trading.execution.algos  use concrete algo modules directly
    _emit()

src\hybrid_ai_trading\algos\__init__.py:45
  C:\Dev\HybridAITrading\src\hybrid_ai_trading\algos\__init__.py:45: RuntimeWarning: hybrid_ai_trading.algos fallback exports due to: No module named 'hybrid_ai_trading.execution.algos.iceberg_executor'
    _w.warn(f"hybrid_ai_trading.algos fallback exports due to: {_e}", RuntimeWarning)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
ERROR tests/engine/test_trade_engine_alert_branches.py
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!
3 warnings, 1 error in 2.68s

---
## 20251103_193248  RiskManager: daily-loss gate sanitation
**Why:** Fix parser-safe block and priority order

**Files:** src\hybrid_ai_trading\risk\risk_manager.py
**Logs:** ./logs/20251103_193248/
**Backups:** ./.backup/*.20251103_193248.bak

**Tests:** python -m pytest -q -k risk_manager_more_cov

**Summary (tail):**
E       def kelly_size(self, edge: float, odds: float, regime: float = 1.0) -> float:
E   IndentationError: unexpected indent
============================== warnings summary ===============================
src\hybrid_ai_trading\algos\__init__.py:24
  C:\Dev\HybridAITrading\src\hybrid_ai_trading\algos\__init__.py:24: Warning: deprecated: hybrid_ai_trading.algos  use concrete algo modules directly
    _emit()

src\hybrid_ai_trading\execution\algos\__init__.py:17
  C:\Dev\HybridAITrading\src\hybrid_ai_trading\execution\algos\__init__.py:17: Warning: deprecated: hybrid_ai_trading.execution.algos  use concrete algo modules directly
    _emit()

src\hybrid_ai_trading\algos\__init__.py:45
  C:\Dev\HybridAITrading\src\hybrid_ai_trading\algos\__init__.py:45: RuntimeWarning: hybrid_ai_trading.algos fallback exports due to: No module named 'hybrid_ai_trading.execution.algos.iceberg_executor'
    _w.warn(f"hybrid_ai_trading.algos fallback exports due to: {_e}", RuntimeWarning)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
ERROR tests/engine/test_trade_engine_alert_branches.py
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!
3 warnings, 1 error in 2.82s

---
## 20251103_194408  RiskManager: clean allow_trade early DAILY_LOSS gate
**Why:** Restore clean block; keep priority; parser-safe

**Files:** src\hybrid_ai_trading\risk\risk_manager.py
**Logs:** ./logs/20251103_194408/
**Backups:** ./.backup/*.20251103_194408.bak

**Tests:** python -m pytest -q -k risk_manager_more_cov

**Summary (tail):**


---
### 2025-11-05  RiskManager hardening
- Add kelly_size() with bounds & exception log
- control_signal() honors absolute daily_loss_limit
- Aggregate Sharpe/Sortino exception logs
- Lowercase leverage message for test stability
- update_equity(): reject negative; critical log
- reset_day(): return reason + exact log string
- Encoding/line-endings: UTF-8 no-BOM, LF
[2025-11-07] Phase 6/7: CodeQL advanced-only; branch-protection contexts; PreMarket smoke; paper runner tests.
## 2025-12-22 � Block-G institutional hardening (Phase5/6/7)

**Goal:** No live NVDA order may bypass Block-G contract (fail-closed).

### What is enforced
- Python: ExecutionEngine + execution_engine_phase5_guard.py enforce Block-G for LIVE (HAT_IS_PAPER=0)
- IB: broker/ib_safe.py provides a single placeOrder chokepoint for raw IB calls; gates NVDA/SPY/QQQ in LIVE
- Contract: blockg_contract.py raises BlockGNotReady for all Block-G failures (no RuntimeError leakage)
- Shared exception: execution/blockg_errors.py eliminates circular imports
- CI/ops: tools/Run-BlockGTestsFirst.ps1 runs the critical Block-G slice first (fail-closed)
- Daily: tools/Run-Phase1ToPhase7Daily.ps1 runs BlockG-first, then producers, then stamp gate (fail-closed)
- Stamp: logs/nvda_live_ready_stamp.json written by tools/Write-NvdaLiveReadyStamp.ps1 (contract-only; deterministic)

### Operator signals
- Daily prints: [DAILY] NVDA LIVE READY ? (stamp ok).
- Daily prints: [DAILY] StampPath=...logs\nvda_live_ready_stamp.json

### Rollback
- Revert commits:
  - 43749759 (shared error type + IB chokepoint + tests)
  - dfc9133a (BlockG-first slice runner)
  - 90053d5c (daily stamp fail-closed)
  - 513acb9f (stamp path banner)
  - 4e25a5ee (stamp writer path fix)

## 2025-12-26 12:23:20 -08:00 — CHECKPOINT_20251226_122033 — BlockG: strict live fail-closed + NVDA live-ready stamp gate + CI gates (#42)
- Merge head: 20e5ab92b7a17b512a8e5ce73dfb58a51c244447
- Scope: Phase-5 safety stack (Block-G contract enforced in live path) + NVDA live-ready stamp gate + CI gates hardening
- Key outcomes:
  - Live orders fail-closed unless Block-G readiness is true
  - NVDA live orders additionally require a valid live-ready stamp (daily arming)
  - ci-gates now runs the institutional gate slice (fast) and is Windows-runner reliable

### Files touched (from merge commit)
.github/workflows/ci-gates.yml
.github/workflows/ci-risk-first.yml
docs/BlockG_Live_Arming.md
docs/BlockG_PreMarket_Playbook.md
docs/Phase5_BlockG_GateScorePolicy.md
src/hybrid_ai_trading/execution/live_ready_stamp.py
src/hybrid_ai_trading/broker/ib_safe.py
src/hybrid_ai_trading/execution/blockg_enforce.py
src/hybrid_ai_trading/execution/blockg_contract*.py
tests/execution/test_nvda_live_stamp_gate.py
tests/execution/test_ib_safe_chokepoint_blockg.py
tools/Run-PreMarketBlockG-Smart.ps1
tools/Arm-NVDA-Live.ps1
tools/Disarm-NVDA-Live.ps1



### Diffstat (from merge commit)
 See PR #42 for full diffstat.



### Validation
- GitHub Checks: CI Risk-First + ci-gates ✅ (PR #42)
- Local spot-check: tests/execution/test_nvda_live_stamp_gate.py ✅

- [2026-01-03 22:01:57] BLOCK-G INSTITUTIONAL LOCK: single-authority PS checker + closed-day semantics + no-bypass + LockPack wired into DailyReadiness.
- [2026-01-03 22:10:36] BLOCKG_LOCK OK: HEAD=67c29b46 TAG=CHECKPOINT_BLOCKG_LOCK_20260103_220202 LOCKPACK_EXIT=0 READY_EXECUTOR=Arm-NVDA-Live only.
