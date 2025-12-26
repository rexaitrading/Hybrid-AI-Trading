
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
.gitignore
audit.csv
backup.csv
configs/blockg_thresholds.override.json
docs/BlockG_Live_Arming.md
docs/BlockG_PreMarket_Playbook.md
docs/CHECKPOINTS.md
docs/OPS_Readiness_Phase1to7.md
docs/PATCHLOG.md
docs/Phase2_3_Diagnostics.md
docs/Phase5_BlockG_GateScorePolicy.md
docs/ROADMAP.md
docs/contracts/blockg_status_stub.template.json
pytest.ini
runners/backtest_replay.py
scripts/preflight_wrapper.ps1
scripts/setup_ibc_and_launch.ps1.BROKEN_QUARANTINED.txt
src/hybrid_ai_trading/broker/ib_safe.py
src/hybrid_ai_trading/brokers/base.py
src/hybrid_ai_trading/brokers/ib_adapter.py
src/hybrid_ai_trading/cost/__init__.py
src/hybrid_ai_trading/costs.py
src/hybrid_ai_trading/data/clients/ibkr_client.py
src/hybrid_ai_trading/execution/algos/iceberg_executor.py
src/hybrid_ai_trading/execution/algos/twap_executor.py
src/hybrid_ai_trading/execution/algos/vwap_executor.py
src/hybrid_ai_trading/execution/blockg_contract.py
src/hybrid_ai_trading/execution/blockg_contract_gate.py
src/hybrid_ai_trading/execution/blockg_contract_reader.py
src/hybrid_ai_trading/execution/blockg_enforce.py
src/hybrid_ai_trading/execution/blockg_errors.py
src/hybrid_ai_trading/execution/blockg_guard.py
src/hybrid_ai_trading/execution/brokers.py
src/hybrid_ai_trading/execution/cost_gate.py
src/hybrid_ai_trading/execution/execution_engine.py
src/hybrid_ai_trading/execution/execution_engine_phase5_guard.py
src/hybrid_ai_trading/execution/live_ready_stamp.py
src/hybrid_ai_trading/execution/order_manager.py
src/hybrid_ai_trading/execution/paper_order.py
src/hybrid_ai_trading/execution/smart_router.py
src/hybrid_ai_trading/gatescore/__init__.py
src/hybrid_ai_trading/gatescore/daily_build.py
src/hybrid_ai_trading/gatescore/io.py
src/hybrid_ai_trading/gatescore/quality.py
src/hybrid_ai_trading/gatescore/schemas.py
src/hybrid_ai_trading/microstructure/regime.py
src/hybrid_ai_trading/optimizer.py
src/hybrid_ai_trading/optimizer/__init__.py
src/hybrid_ai_trading/order_manager.py
src/hybrid_ai_trading/phase2/__init__.py
src/hybrid_ai_trading/phase2/micro_cost_snapshot.py
src/hybrid_ai_trading/phase2/run_from_phase1.py
src/hybrid_ai_trading/phase4/__init__.py
src/hybrid_ai_trading/phase6/daily_summary.py
src/hybrid_ai_trading/phase7/optimizer.py
src/hybrid_ai_trading/pipelines/daily_close.py
src/hybrid_ai_trading/pipelines/daily_stock_dashboard.py
src/hybrid_ai_trading/portfolio/__init__.py
src/hybrid_ai_trading/portfolio/halts.py
src/hybrid_ai_trading/portfolio/portfolio_tracker.py
src/hybrid_ai_trading/replay/__init__.py
src/hybrid_ai_trading/replay/fill_models.py
src/hybrid_ai_trading/replay/latency_models.py
src/hybrid_ai_trading/replay/replay_multi_day.py
src/hybrid_ai_trading/replay/replay_session.py
src/hybrid_ai_trading/risk/risk_manager.py
src/hybrid_ai_trading/risk_manager.py
src/hybrid_ai_trading/runners/ah_once.py
src/hybrid_ai_trading/runners/backtest_replay.py
src/hybrid_ai_trading/runners/nvda_paperlive_today.py
src/hybrid_ai_trading/runners/replay_micro.py
src/hybrid_ai_trading/runners/runner_stream.py
src/hybrid_ai_trading/runtime/__init__.py
src/hybrid_ai_trading/runtime/run_context.py
src/hybrid_ai_trading/runtime/run_context_reader.py
src/hybrid_ai_trading/trade_engine.py
src/hybrid_ai_trading/utils/preflight.py
src/hybrid_ai_trading/utils/risk.py
tests/conftest.py
tests/engine/test_trade_engine_algo_invalid_status.py
tests/engine/test_trade_engine_branch_exact.py
tests/execution/test_blockg_gatescore_policy_session_age.py
tests/execution/test_blockg_ib_placeorder_guard.py
tests/execution/test_blockg_order_manager_guard.py
tests/execution/test_ib_safe_chokepoint_blockg.py
tests/execution/test_nvda_live_stamp_gate.py
tests/execution/test_order_manager_blockg_defense_in_depth.py
tests/execution/test_order_manager_blocks_before_broker.py
tests/execution/test_paper_order_live_guard.py
tests/risk/test_regime_detector_full.py
tests/test_blockg_broker_base_guard.py
tests/test_blockg_chokepoint_blocks_live.py
tests/test_blockg_enforce.py
tests/test_blockg_enforce_live_order_path.py
tests/test_blockg_risk_flatten_guard.py
tests/test_daily_close_full.py
tests/test_gatescore_fresh_policy.py
tests/test_ib_adapter_blockg_enforce.py
tests/test_microstructure_regime.py
tests/test_no_direct_ib_placeorder.py
tests/test_phase1_backtest_replay_smoke.py
tests/test_phase1_replay_demo.py
tests/test_phase2_cost_gate.py
tests/test_phase2_cost_gate_latency.py
tests/test_phase2_cost_gate_wiring.py
tests/test_phase2_costs_package.py
tests/test_phase3_gatescore_daily_build_cli.py
tests/test_phase3_gatescore_quality.py
tests/test_phase4_validation_stamp.py
tests/test_phase5_ev_bands_basic.py
tests/test_phase5_todayness_contract.py
tests/test_phase6_portfolio_halt_blocks.py
tests/test_phase7_optimizer_stub.py
tests/test_portfolio_tracker_full.py
tests/test_runcontext_precedence.py
tests/unified/test_risk_layer_suite.py
tools/Arm-NVDA-Live.ps1
tools/Assert-RepoPython.ps1
tools/Audit-IBGTasks.ps1
tools/Audit-Phase1ToPhase7Ready.ps1
tools/Audit-Phases.ps1
tools/Build-BlockGStatusStub.ps1
tools/Build-EvHardEvidenceRaw.ps1
tools/Build-EvHardSnapshot.ps1
tools/Build-GateScoreDailySummary.ps1
tools/Build-GateScorePnlSummary.ps1
tools/Build-NotionNvdaLiveAllowedPayload.ps1
tools/Build-NotionQqqLiveAllowedPayload.ps1
tools/Build-NotionSpyLiveAllowedPayload.ps1
tools/Build-Phase2MicroCostSnapshot.ps1
tools/Build-Phase6PortfolioState.ps1
tools/Build-RunContextStub.ps1
tools/Capture-IBGDeathContext.ps1
tools/Check-BlockGReady.ps1
tools/Check-GateScoreAge.ps1
tools/Check-IBGReady.ps1
tools/Check-NoRawPythonTools.ps1
tools/Check-Phase4Today.ps1
tools/Check-Phase5Today.ps1
tools/Check-PreMarketInputs.ps1
tools/Compute-Phase5EvHardSnapshotInput.ps1
tools/Disarm-NVDA-Live.ps1
tools/Expand-SpyPaperliveToday.ps1
tools/Export-BlockGStatusForNotion.ps1
tools/Export-NvdaPaperliveResultsToday.ps1
tools/Export-Phase1ReplayForNotion.ps1
tools/Export-Phase5EvHardVetoDailySnapshot.ps1
tools/Export-Phase5SafetyRunContextCsv.ps1
tools/Find-IbPlaceOrder.ps1
tools/Invoke-BlockGCheck.ps1
tools/Invoke-BlockGPreflight.ps1
tools/Ops-24x7.ps1
tools/PreMarket-OneTap.ps1
tools/Probe-IbApiReady.ps1
tools/Push-NotionNvdaLiveAllowed.ps1
tools/RootCause-Sweep.ps1
tools/Run-Audit-Phases.ps1
tools/Run-BlockGTestsFirst.ps1
tools/Run-BuildGateScoreSummaries.ps1
tools/Run-DailyProducersSuite.ps1
tools/Run-EvHardVetoDaily.ps1
tools/Run-GateScoreDailyBuild.ps1
tools/Run-GateScoreDailySummary.ps1
tools/Run-IntelPipeline-Minimal.ps1
tools/Run-IntelPipeline.ps1
tools/Run-NvdaPaperliveToday.ps1
tools/Run-Phase1ReplayDeterministic.ps1
tools/Run-Phase1ReplayMultiDay.ps1
tools/Run-Phase1ReplayRealCsv.ps1
tools/Run-Phase1ToPhase7Daily.ps1
tools/Run-Phase23HealthDaily.ps1
tools/Run-Phase2FromPhase1.ps1
tools/Run-Phase3GateScoreDaily.ps1
tools/Run-Phase4Stamp.ps1
tools/Run-Phase4Validation.ps1
tools/Run-Phase5SafetySnapshot.ps1
tools/Run-Phase5SafetySuite.ps1
tools/Run-Phase5Tests.ps1
tools/Run-Phase7OptimizerDaily.ps1
tools/Run-PhaseSweep7.ps1
tools/Run-PreMarketAll.ps1
tools/Run-PreMarketBlockG-Smart.ps1
tools/Run-PreMarketBlockG.ps1
tools/Run-PreMarketOneTapGatedNvda.ps1
tools/Run-PytestFromRepo.ps1
tools/Sanitize-NvdaLiveReadyStamp.ps1
tools/Show-BlockGThresholds.ps1
tools/Show-Phase5SafetyState.ps1
tools/Smoke-LiveIbFailClosed.ps1
tools/Start-IBGWatchdog.ps1
tools/Test-NotionDbVisible.ps1
tools/Test-Phase6Phase7Ops.ps1
tools/Update-NotionNvdaLiveAllowed.ps1
tools/Watch-IBGDeath.ps1
tools/Write-EvHardVetoSnapshot.ps1
tools/Write-GateScoreDailyFromBlockG.ps1
tools/Write-NvdaGateScoreEventsFromPaperlive.ps1
tools/Write-NvdaLiveReadyStamp.ps1
tools/Write-Phase23HealthDaily.ps1
tools/Write-Phase4PassedStamp.ps1
tools/Write-QqqGateScoreEventsFromPaperlive.ps1
tools/Write-QqqLiveReadyStamp.ps1
tools/Write-RunJournalTemplate.ps1
tools/Write-SpyGateScoreEventsFromPaperlive.ps1
tools/Write-SpyLiveReadyStamp.ps1
tools/Write-SpyQqqGateScoreEventsStub.ps1
tools/_RunContext.ps1
tools/ibg_repo_smoke_readonly.py
tools/python.ps1
tools/smoke/smoke_blockg_contract_enforcement.py
tools/spy_qqq_microstructure_enrich.py
tools/start_stream_realtime.ps1
tools/stream.ps1

### Diffstat (from merge commit)
 .github/workflows/ci-gates.yml                     |  41 ++
 .github/workflows/ci-risk-first.yml                |  63 +++
 .gitignore                                         |  14 +
 audit.csv                                          | 277 ------------
 backup.csv                                         | 277 ------------
 configs/blockg_thresholds.override.json            |  26 ++
 docs/BlockG_Live_Arming.md                         |  35 ++
 docs/BlockG_PreMarket_Playbook.md                  |  20 +
 docs/CHECKPOINTS.md                                |  12 +
 docs/OPS_Readiness_Phase1to7.md                    |  20 +
 docs/PATCHLOG.md                                   |  24 ++
 docs/Phase2_3_Diagnostics.md                       |  13 +
 docs/Phase5_BlockG_GateScorePolicy.md              |  15 +
 docs/ROADMAP.md                                    |   4 +
 docs/contracts/blockg_status_stub.template.json    |  28 ++
 pytest.ini                                         |  24 +-
 runners/backtest_replay.py                         | 112 +++++
 scripts/preflight_wrapper.ps1                      |  23 +-
 ...etup_ibc_and_launch.ps1.BROKEN_QUARANTINED.txt} |  22 +-
 src/hybrid_ai_trading/broker/ib_safe.py            | 386 +++++++++--------
 src/hybrid_ai_trading/brokers/base.py              |  18 +
 src/hybrid_ai_trading/brokers/ib_adapter.py        |  43 +-
 src/hybrid_ai_trading/cost/__init__.py             |   6 +
 src/hybrid_ai_trading/costs.py                     |  31 ++
 src/hybrid_ai_trading/data/clients/ibkr_client.py  |   5 +-
 .../execution/algos/iceberg_executor.py            |  16 +
 .../execution/algos/twap_executor.py               |  16 +
 .../execution/algos/vwap_executor.py               |  16 +
 src/hybrid_ai_trading/execution/blockg_contract.py | 179 ++++++++
 .../execution/blockg_contract_gate.py              |  99 +++++
 .../execution/blockg_contract_reader.py            |  59 +++
 src/hybrid_ai_trading/execution/blockg_enforce.py  |  84 ++++
 src/hybrid_ai_trading/execution/blockg_errors.py   |   6 +
 src/hybrid_ai_trading/execution/blockg_guard.py    |  26 ++
 src/hybrid_ai_trading/execution/brokers.py         |  26 +-
 src/hybrid_ai_trading/execution/cost_gate.py       |  61 +++
 .../execution/execution_engine.py                  |  50 ++-
 .../execution/execution_engine_phase5_guard.py     |  36 +-
 .../execution/live_ready_stamp.py                  |  58 +++
 src/hybrid_ai_trading/execution/order_manager.py   |  52 ++-
 src/hybrid_ai_trading/execution/paper_order.py     |  23 +
 src/hybrid_ai_trading/execution/smart_router.py    |  13 +-
 src/hybrid_ai_trading/gatescore/__init__.py        |  16 +
 src/hybrid_ai_trading/gatescore/daily_build.py     |  71 +++
 src/hybrid_ai_trading/gatescore/io.py              |  55 +++
 src/hybrid_ai_trading/gatescore/quality.py         |  40 ++
 src/hybrid_ai_trading/gatescore/schemas.py         |  23 +
 src/hybrid_ai_trading/microstructure/regime.py     |   9 +
 src/hybrid_ai_trading/optimizer.py                 |  36 ++
 src/hybrid_ai_trading/optimizer/__init__.py        |  29 ++
 src/hybrid_ai_trading/order_manager.py             |  12 +
 src/hybrid_ai_trading/phase2/__init__.py           |   1 +
 .../phase2/micro_cost_snapshot.py                  |  23 +
 src/hybrid_ai_trading/phase2/run_from_phase1.py    | 155 +++++++
 src/hybrid_ai_trading/phase4/__init__.py           |   4 +
 src/hybrid_ai_trading/phase6/daily_summary.py      | 214 ++++++++++
 src/hybrid_ai_trading/phase7/optimizer.py          | 177 ++++++++
 src/hybrid_ai_trading/pipelines/daily_close.py     |   4 +-
 .../pipelines/daily_stock_dashboard.py             |  14 +-
 src/hybrid_ai_trading/portfolio/__init__.py        |   9 +-
 src/hybrid_ai_trading/portfolio/halts.py           |  51 +++
 .../portfolio/portfolio_tracker.py                 |   7 +
 src/hybrid_ai_trading/replay/__init__.py           |   1 +
 src/hybrid_ai_trading/replay/fill_models.py        |  36 ++
 src/hybrid_ai_trading/replay/latency_models.py     |  15 +
 src/hybrid_ai_trading/replay/replay_multi_day.py   |  98 +++++
 src/hybrid_ai_trading/replay/replay_session.py     |  61 +++
 src/hybrid_ai_trading/risk/risk_manager.py         | 475 ++++++++++++++++-----
 src/hybrid_ai_trading/risk_manager.py              | 155 +------
 src/hybrid_ai_trading/runners/ah_once.py           |   9 +-
 src/hybrid_ai_trading/runners/backtest_replay.py   | 100 ++++-
 .../runners/nvda_paperlive_today.py                |  66 +++
 src/hybrid_ai_trading/runners/replay_micro.py      |  27 ++
 src/hybrid_ai_trading/runners/runner_stream.py     |  55 ++-
 src/hybrid_ai_trading/runtime/__init__.py          |   1 +
 src/hybrid_ai_trading/runtime/run_context.py       |  89 ++++
 .../runtime/run_context_reader.py                  |  81 ++++
 src/hybrid_ai_trading/trade_engine.py              |  35 +-
 src/hybrid_ai_trading/utils/preflight.py           |  10 +-
 src/hybrid_ai_trading/utils/risk.py                |  31 +-
 tests/conftest.py                                  | 112 ++---
 .../test_trade_engine_algo_invalid_status.py       |   4 +-
 tests/engine/test_trade_engine_branch_exact.py     |   6 +-
 .../test_blockg_gatescore_policy_session_age.py    |  36 ++
 tests/execution/test_blockg_ib_placeorder_guard.py |  98 +++++
 tests/execution/test_blockg_order_manager_guard.py |  97 +++++
 tests/execution/test_ib_safe_chokepoint_blockg.py  |  98 +++++
 tests/execution/test_nvda_live_stamp_gate.py       |  30 ++
 .../test_order_manager_blockg_defense_in_depth.py  |  44 ++
 .../test_order_manager_blocks_before_broker.py     |  64 +++
 tests/execution/test_paper_order_live_guard.py     |  47 ++
 tests/risk/test_regime_detector_full.py            |   8 +-
 tests/test_blockg_broker_base_guard.py             |  28 ++
 tests/test_blockg_chokepoint_blocks_live.py        |  43 ++
 tests/test_blockg_enforce.py                       |  19 +
 tests/test_blockg_enforce_live_order_path.py       |  80 ++++
 tests/test_blockg_risk_flatten_guard.py            |  58 +++
 tests/test_daily_close_full.py                     |   7 +-
 tests/test_gatescore_fresh_policy.py               |  53 +++
 tests/test_ib_adapter_blockg_enforce.py            |  28 ++
 tests/test_microstructure_regime.py                |  15 +
 tests/test_no_direct_ib_placeorder.py              |  42 ++
 tests/test_phase1_backtest_replay_smoke.py         |  25 ++
 tests/test_phase1_replay_demo.py                   |  12 +-
 tests/test_phase2_cost_gate.py                     |  14 +
 tests/test_phase2_cost_gate_latency.py             |  19 +
 tests/test_phase2_cost_gate_wiring.py              |  41 ++
 tests/test_phase2_costs_package.py                 |   8 +
 tests/test_phase3_gatescore_daily_build_cli.py     |  25 ++
 tests/test_phase3_gatescore_quality.py             |  27 ++
 tests/test_phase4_validation_stamp.py              |  16 +
 tests/test_phase5_ev_bands_basic.py                |   5 +
 tests/test_phase5_todayness_contract.py            |  82 ++++
 tests/test_phase6_portfolio_halt_blocks.py         |  29 ++
 tests/test_phase7_optimizer_stub.py                |  14 +
 tests/test_portfolio_tracker_full.py               |  67 ++-
 tests/test_runcontext_precedence.py                |  12 +
 tests/unified/test_risk_layer_suite.py             |   9 +-
 tools/Arm-NVDA-Live.ps1                            |  74 ++++
 tools/Assert-RepoPython.ps1                        |  47 ++
 tools/Audit-IBGTasks.ps1                           |  24 ++
 tools/Audit-Phase1ToPhase7Ready.ps1                |  63 +++
 tools/Audit-Phases.ps1                             |  86 ++++
 tools/Build-BlockGStatusStub.ps1                   | 435 ++++++++++++-------
 tools/Build-EvHardEvidenceRaw.ps1                  | 124 ++++++
 tools/Build-EvHardSnapshot.ps1                     |  69 +++
 tools/Build-GateScoreDailySummary.ps1              |  91 +++-
 tools/Build-GateScorePnlSummary.ps1                | 213 +++++++++
 tools/Build-NotionNvdaLiveAllowedPayload.ps1       | 128 ++++++
 tools/Build-NotionQqqLiveAllowedPayload.ps1        | 127 ++++++
 tools/Build-NotionSpyLiveAllowedPayload.ps1        | 127 ++++++
 tools/Build-Phase2MicroCostSnapshot.ps1            |  71 +++
 tools/Build-Phase6PortfolioState.ps1               |  47 ++
 tools/Build-RunContextStub.ps1                     |  64 ++-
 tools/Capture-IBGDeathContext.ps1                  |  46 ++
 tools/Check-BlockGReady.ps1                        | 176 ++++----
 tools/Check-GateScoreAge.ps1                       |  26 ++
 tools/Check-IBGReady.ps1                           |  45 ++
 tools/Check-NoRawPythonTools.ps1                   |  23 +
 tools/Check-Phase4Today.ps1                        |  22 +
 tools/Check-Phase5Today.ps1                        |  76 ++++
 tools/Check-PreMarketInputs.ps1                    |  53 +++
 tools/Compute-Phase5EvHardSnapshotInput.ps1        |  86 ++++
 tools/Disarm-NVDA-Live.ps1                         |  54 +++
 tools/Expand-SpyPaperliveToday.ps1                 |  48 +++
 tools/Export-BlockGStatusForNotion.ps1             |  37 ++
 tools/Export-NvdaPaperliveResultsToday.ps1         |  70 +++
 tools/Export-Phase1ReplayForNotion.ps1             |  72 ++++
 tools/Export-Phase5EvHardVetoDailySnapshot.ps1     |  96 +++++
 tools/Export-Phase5SafetyRunContextCsv.ps1         |  20 +-
 tools/Find-IbPlaceOrder.ps1                        |  25 ++
 tools/Invoke-BlockGCheck.ps1                       |  37 ++
 tools/Invoke-BlockGPreflight.ps1                   |  22 +
 tools/Ops-24x7.ps1                                 | 130 ++++++
 tools/PreMarket-OneTap.ps1                         |  78 +++-
 tools/Probe-IbApiReady.ps1                         |  48 +++
 tools/Push-NotionNvdaLiveAllowed.ps1               | 120 ++++++
 tools/RootCause-Sweep.ps1                          |  46 ++
 tools/Run-Audit-Phases.ps1                         |  39 ++
 tools/Run-BlockGTestsFirst.ps1                     |  15 +
 tools/Run-BuildGateScoreSummaries.ps1              |  15 +
 tools/Run-DailyProducersSuite.ps1                  |  52 +++
 tools/Run-EvHardVetoDaily.ps1                      |  60 +++
 tools/Run-GateScoreDailyBuild.ps1                  | 150 +++++++
 tools/Run-GateScoreDailySummary.ps1                |  79 ++++
 tools/Run-IntelPipeline-Minimal.ps1                |  48 +++
 tools/Run-IntelPipeline.ps1                        |  53 +++
 tools/Run-NvdaPaperliveToday.ps1                   |  49 +++
 tools/Run-Phase1ReplayDeterministic.ps1            |  73 ++++
 tools/Run-Phase1ReplayMultiDay.ps1                 |  22 +
 tools/Run-Phase1ReplayRealCsv.ps1                  |  56 +++
 tools/Run-Phase1ToPhase7Daily.ps1                  | 120 ++++++
 tools/Run-Phase23HealthDaily.ps1                   |  77 ++++
 tools/Run-Phase2FromPhase1.ps1                     |  23 +
 tools/Run-Phase3GateScoreDaily.ps1                 |  88 ++--
 tools/Run-Phase4Stamp.ps1                          | 127 ++++++
 tools/Run-Phase4Validation.ps1                     | 114 +++--
 tools/Run-Phase5SafetySnapshot.ps1                 |  60 +--
 tools/Run-Phase5SafetySuite.ps1                    |  18 +
 tools/Run-Phase5Tests.ps1                          |  21 +
 tools/Run-Phase7OptimizerDaily.ps1                 | 205 +++++++++
 tools/Run-PhaseSweep7.ps1                          | 120 ++++++
 tools/Run-PreMarketAll.ps1                         |  55 +++
 tools/Run-PreMarketBlockG-Smart.ps1                |  37 ++
 tools/Run-PreMarketBlockG.ps1                      | 143 +++++++
 tools/Run-PreMarketOneTapGatedNvda.ps1             | 112 ++++-
 tools/Run-PytestFromRepo.ps1                       |  41 ++
 tools/Sanitize-NvdaLiveReadyStamp.ps1              |  52 +++
 tools/Show-BlockGThresholds.ps1                    |  30 ++
 tools/Show-Phase5SafetyState.ps1                   |  20 +-
 tools/Smoke-LiveIbFailClosed.ps1                   |  83 ++++
 tools/Start-IBGWatchdog.ps1                        |  26 ++
 tools/Test-NotionDbVisible.ps1                     |  45 ++
 tools/Test-Phase6Phase7Ops.ps1                     |  83 ++++
 tools/Update-NotionNvdaLiveAllowed.ps1             |  19 +
 tools/Watch-IBGDeath.ps1                           |  42 ++
 tools/Write-EvHardVetoSnapshot.ps1                 |  31 ++
 tools/Write-GateScoreDailyFromBlockG.ps1           |  73 ++++
 tools/Write-NvdaGateScoreEventsFromPaperlive.ps1   | 145 +++++++
 tools/Write-NvdaLiveReadyStamp.ps1                 |  66 +++
 tools/Write-Phase23HealthDaily.ps1                 |  56 +++
 tools/Write-Phase4PassedStamp.ps1                  |  24 ++
 tools/Write-QqqGateScoreEventsFromPaperlive.ps1    | 145 +++++++
 tools/Write-QqqLiveReadyStamp.ps1                  |  66 +++
 tools/Write-RunJournalTemplate.ps1                 |  65 +++
 tools/Write-SpyGateScoreEventsFromPaperlive.ps1    |  90 ++++
 tools/Write-SpyLiveReadyStamp.ps1                  |  66 +++
 tools/Write-SpyQqqGateScoreEventsStub.ps1          |  44 ++
 tools/_RunContext.ps1                              |  11 +
 tools/ibg_repo_smoke_readonly.py                   |  21 +
 tools/python.ps1                                   |  17 +
 tools/smoke/smoke_blockg_contract_enforcement.py   |  45 ++
 tools/spy_qqq_microstructure_enrich.py             |  70 ++-
 tools/start_stream_realtime.ps1                    |   3 +-
 tools/stream.ps1                                   | 221 +++-------
 215 files changed, 11217 insertions(+), 1836 deletions(-)

### Validation
- GitHub Checks: CI Risk-First + ci-gates ✅ (PR #42)
- Local spot-check: tests/execution/test_nvda_live_stamp_gate.py ✅

