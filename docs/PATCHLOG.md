---
## 2026-01-13 - Phase-4 Todayness (per-market) Root-Cause Gate + Hygiene

Goal:
- Prove true root causes for Phase-4 per-market todayness before any execution changes.

Hard proof (CHECK):
- Missing per-market Phase-4 validation stamp files:
  - logs/JP/phase4_validation_passed.json (missing)
  - logs/HK/phase4_validation_passed.json (missing)
  - logs/SG/phase4_validation_passed.json (missing)
  - Global + US exist.
- Run-Phase4Validation.ps1 (observed in line-anchored proof during CHECK) had:
  - Copy-before-write ordering bug (copied logs/phase4_validation_passed.json before writing new stamp)
  - Wrong date authority (as_of_date derived from Get-Date yyyy-MM-dd, not RunContext/HAT_ASOF_DATE)
- Schema note: global stamp includes exit_code/reason; US stamp uses notes and omits exit_code/reason.

Hygiene action (EXECUTE Step 0.1):
- Captured WIP diff as UTF-8 no-BOM patch (forensics) and restored clean working tree:
  - logs/_quarantine/phase4validation_wip_20260113_132932.patch

Must NOT change:
- Fail-closed semantics
- Paper safety boundaries
- Block-G semantic owner authority

Next planned fix (SPEC only; not executed yet):
- Update Phase-4 harness to write per-market validation_passed directly (no copy-before-write)
- Source as_of_date from RunContext/HAT_ASOF_DATE (market authority), not local Get-Date.
---
---
## 2026-01-11 - Ops: Add Verify-BlockG-Ready one-shot premarket gate

Commit: 9c50b406

Adds tools/Verify-BlockG-Ready.ps1:
- Builds Block-G status stub (FULL semantics; does NOT force FAST)
- Runs Check-BlockGReady (default NVDA; optional -All)
- Exits 0 only when READY; otherwise exits 2 (fail-closed)

Validation (Sunday):
- Expected fail-closed on market_closed_today => exit=2

---
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
## 2026-01-11 15:30:24  Block-G enforcement hardening + test stabilization

- FIX: Block-G tests stabilized (contract_semantics_level fixtures, live-arm token today-ness, strict-markers db marker).
- FIX: OrderManager live submit removed IB-like bypass; Block-G enforced for NVDA/SPY/QQQ regardless of broker client type.
- VALIDATION: pytest -k blockg (22 passed), pytest -k "order_manager and blockg" (3 passed).
- CHECKPOINTS: CHECKPOINT_20260111_BLOCKG_GREEN, CHECKPOINT_20260111_BLOCKG_NO_BYPASS
## 2026-01-11 15:51:50  Block-G contract A(2) coherence: gsAsOf fallback + ok_today semantics

- FIX: Builder derives gatescore_as_of_date from resolved events tail when summary CSV is blank (prevents empty gsAsOf).
- FIX: gatescore_ok_today now strictly requires gsAsOf == todayLocal (no stale ok_today).
- FIX: gatescore_ok_today / gatescore_ok_live_today coherent with freshness + age policy.
- VALIDATION: Build-BlockGStatusStub FULL emits gsAsOf=2026-01-10 (age=1), ok_today=false on 2026-01-11; pytest -k blockg green.
- CHECKPOINT: CHECKPOINT_20260111_BLOCKG_A2_COHERENCE
### 2026-01-14 21:27:57 — RC7 fix: NVDA paperlive today uses market as_of_date (JP fail-closed)
- src: nvda_paperlive_today.py now accepts --market/--as-of-date (env:HAT_MARKET/HAT_ASOF_DATE); non-US requires as-of-date; no fake stamping.
- tools: Run-NvdaPaperliveToday.ps1 now passes market/as_of_date and defaults OutPath to logs\<Market>\nvda_phase5_paperlive_results_today.jsonl (fail-closed non-US).

## 2026-01-15 14:44:41 — Phase-1 foundation sweep: exclude paperlive from stamp detection (CHECK-only)
- Added tools/CHECK-Phase1FoundationSweep.ps1 to run a consolidated Phase-1 evidence sweep across US/HK/SG/JP/KR/TW.
- Root cause: prior stamp scan matched live inside paperlive causing false FAIL-CLOSED.
- Fix: exclude paperlive filenames; tighten live detection to token-ish match; keep fail-closed semantics.
- Proof: PHASE1_SWEEP_OK=TRUE and STAMP_HITS=NONE for all markets.
## 2026-01-16 15:45:06 — A1 OrderManager hardening (risk wiring + meta0 crash fix)
- Fix root OrderManager meta0 NameError by defining meta0 = _merge_meta_ctx(meta, ctx, symbol) in buy/sell market+limit methods (prevents shadow entrypoint crash/bypass ambiguity).
- Fix execution OrderManager: accept risk_manager=... wiring (prevents silent risk_veto disable).
- Remove LIVE ambiguity: ensure_symbol_blockg_ready(... allow_paper=False, is_paper=False ...) (defense-in-depth; no functional change today).
- Reversible backups: *.bak_20260116_154506_A1_OM
## 2026-01-17 00:15:24 — Mode drift cleanup: canonical HAT_MODE single truth (LIVE/PAPERLIVE/PAPER)
- Added tools/Resolve-HatRunMode.ps1 as the single semantic authority for runtime lane.
- Removed direct $env:HAT_MODE parsing from Block-G + Global-Ready builders + RunContext; consumers now use canonical run_mode.
- Preserved LIVE fail-closed guards: Run-OneTap-WhenRTH refuses LIVE; Phase5 paperlive evidence copy refuses LIVE.
- Validation: Resolve-HatRunMode returns correct flags for PAPERLIVE/LIVE; original-surface scan shows zero remaining direct HAT_MODE parses; LIVE guard checks fail-closed as expected.
- CHECKPOINT: CHECKPOINT_20260117_MODEDRIFT_A1e
## 2026-01-17 00:43:00 — A2 closed-day effective audit semantics + OneTap summary harden
- A2: EffectiveOk returns null when not_evaluated_market_closed=true (prevents false contradictions vs stub on weekends/holidays).
- OneTap: guard missing stub fields; reasons_not_ready computed outside hash literal (parser-safe under StrictMode).
- Validation: PAPERLIVE OneTap smoke => A2 OK + onetap_summary.json emitted.
- CHECKPOINT: CHECKPOINT_20260117_A2_CLOSED_DAY_AUDIT_GREEN
## 2026-01-17 00:49:00 — KR A2 closed-day semantics: fail-closed when RunContext missing
- Fix: Write-Phase23Status / Write-EvHardStatus now fail-closed to market_closed_today when RunContext is missing/unreadable (prevents blank reason/not_evaluated fields).
- Result: KR phase23_status.json and ev_hard_status.json now emit ok_today=false + not_evaluated_market_closed=true + reason=market_closed_today on closed days.
- CHECKPOINT: CHECKPOINT_20260117_KR_CLOSED_DAY_SEMANTICS_GREEN
## 2026-01-18 01:16:45 � Trade labeling + AAR scaffolding (US/PAPERLIVE proofed)

**New tools:**
- `tools/Build-TradeLabels.ps1` � writes `trade_labels.jsonl` from orders + gatescore (+ optional sim/regime inputs), truth-preserving.
- `tools/Build-DailyAAR.ps1` � generates `daily_aar.md` from `trade_labels.jsonl` only (no guessing).
- `tools/Build-Counterfactuals.ps1` � truth-preserving stub: writes blocked record when bars cache missing.

**Hard-proven fixes inside TradeLabels:**
- Brace mismatch in `Pick-GS` from non-balanced replacement ? removed extra `}` at line 117.
- `if` used as expression inside hashtable (`= (if(...))`) ? converted to `= $(if(...){...} else {...})`.

**Verification:**
- Parse: `Parser.ParseFile` captured-errors ? **PARSE_OK** (all 3 tools)
- Runtime: `Build-TradeLabels.ps1 -Market US -Symbol NVDA -Mode PAPERLIVE` ? wrote `logs/US/trade_labels.jsonl` (1 row)

**Scope:** tools/Build-TradeLabels.ps1, tools/Build-DailyAAR.ps1, tools/Build-Counterfactuals.ps1


## 2026-01-18 16:20:45 — Fix RunContext TradeMode single-truth (PAPERLIVE)
- Root cause proven: Resolve-RunContext default TradeMode=PAPER blocked Resolve-HatRunMode PAPERLIVE.
- Change: Set default TradeMode to empty string so single-truth applies.
- Proof: Resolve-HatRunMode run_mode=PAPERLIVE matches Resolve-RunContext trade_mode=PAPERLIVE.


## 2026-01-18 16:29:15 — GateScore: write TODAY slice to *_gatescore_events_today.jsonl (stop clobbering ledger)
- Root cause proven: Build-GateScoreEvents-Today called writer with -Mode rewrite, forcing single-day events and rolling=0.
- Change: Build-GateScoreEvents-Today now writes *_gatescore_events_today.jsonl (today slice).
- Next: BlockG will read today slice for freshness/eligible counts while ledger remains for rolling.


## 2026-01-18 16:40:18 — BlockG: use *_gatescore_events_today.jsonl for today-only checks; keep ledger for rolling
- Root cause proven: GateScore ledger was overwritten daily (single as_of_date) so rolling samples stayed 0.
- Change: Added Resolve-GatescoreEventsPathToday and rewired today-only reads (freshness/eligibleToday/metrics_source).
- Rolling and other historical reads continue using *_gatescore_events.jsonl.


## 2026-01-18 16:44:19 — BlockG: gatescore_recent_enough now reflects policy (age-days), add diag field
- Root cause proven: payload used gsRecentEnough_diag (diagnostic) causing recent_enough=false even when age_days=0.
- Change: gatescore_recent_enough = gsRecentEnough (policy truth); added gatescore_recent_enough_diag for audit.
- Proof: age_days=0 => recent_enough=True while diag can remain False.


## 2026-01-18 16:50:07 — GateScore ledger: default per-market writer Mode=append (multi-day accumulation)
- Root cause proven: Write-GateScoreEvents-PerMarket default Mode=rewrite overwrote nvda_gatescore_events.jsonl each run, preventing rolling.
- Change: default Mode=append; rewrite remains available manually.
- Proof: per-market run reports mode=append and ledger lines increase (e.g., 360 -> 720).

