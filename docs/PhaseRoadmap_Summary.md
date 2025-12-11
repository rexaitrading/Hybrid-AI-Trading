# Phase Roadmap – Snapshot (2025-12-11)

## Phase 1 – Bar Replay / Research Harness
- Status: **IN PROGRESS** (branch: `feature/phase1-bar-replay`)
- Goal:
  - Stable bar-replay to JSONL/CSV.
  - Easy walk-forward and EV/gap sweep for NVDA/SPY/QQQ.
- Next:
  - Finish remaining tests and CI wiring.
  - Merge into main once fully green.

## Phase 2 – Microstructure + Cost Model
- Status: **ACTIVE (SPY/QQQ ORB micro + cost stub wired).**
- Artifacts:
  - `logs\spy_phase5_paper_for_notion_ev_diag_micro.csv`
  - `logs\qqq_phase5_paper_for_notion_ev_diag_micro.csv`
  - `logs\spy_qqq_micro_for_notion.csv`
- Tools:
  - `tools\spy_qqq_microstructure_enrich.py` (log-only enrichment + diagnostics).
  - `tools\Show-SpyQqqCostModel.ps1`, `tools\Show-SpyQqqMicrostructureReport.ps1` (reporting).
- Next:
  - Feed spread/fee estimates and microstructure flags into Phase-5 risk sizing
    and EV-band tuning.

## Phase 3 – GateScore Engine
- Status: **ACTIVE (NVDA GateScore replay + daily suite + Notion export).**
- Artifacts:
  - `logs\gatescore_pnl_summary.csv` (per-signal PnL + micro scores).
  - `logs\gatescore_daily_summary.csv` (daily summary).
  - `logs\nvda_gatescore_for_notion.csv` (Notion import).
- Code & tools:
  - `src\hybrid_ai_trading\replay\nvda_bplus_gate_score.py`
    (`GateScoreHealth`, `load_nvda_gatescore_health`).
  - `tools\_nvda_gate_score_smoke.py`
    (fails if `count_signals < 3` or `pnl_samples < 1`).
  - `tools\Run-GateScoreSmoke.ps1`, `tools\Run-GateScoreDailySuite.ps1`,
    `tools\Run-Phase3GateScoreDaily.ps1`.
- Next:
  - Extend GateScore coverage to SPY/QQQ once enough samples exist.
  - Keep daily GateScore as a hard Block-G prerequisite.

## Phase 4 – Validation Harness
- Status: **ACTIVE (Run-Phase4Validation harness + Block-G hook).**
- Harness:
  - `tools\Run-Phase4Validation.ps1` runs:
    - Phase-1 NVDA replay pytest smoke (`tests\test_phase1_replay_demo.py`).
    - Phase-5 risk + guard slice:
      - EV-bands, combined gates, daily loss cap.
      - Execution-engine Phase-5 guard + IB Phase-5 guard tests.
- Integration:
  - Called directly by operators via `Run-Phase4Validation.ps1`.
  - Also invoked inside `tools\Run-BlockGReadiness.ps1`
    (Phase-5 Block-G checklist) and the daily playbook.
- Next:
  - Keep this slice fast and green as new risk/guard components are added.

## Phase 5 – Controlled Live (NVDA_BPLUS_LIVE + SPY_ORB_LIVE + QQQ_ORB_LIVE)
- Status: **SAFETY STACK WIRED; NVDA LIVE GATED BY BLOCK-G; SPY/QQQ STILL BLOCKED.**
- Safety layers:
  - **Block-G contract**:
    - Status JSON: `logs\blockg_status_stub.json`
      (`phase23_health_ok_today`, `ev_hard_daily_ok_today`,
       `gatescore_fresh_today`, `nvda_blockg_ready`, `spy_blockg_ready`,
       `qqq_blockg_ready`).
  - **RunContext**:
    - `logs\runcontext_phase5_stub.json`
    - `logs\phase5_safety_runcontext_daily.csv` (Notion import for daily safety).
  - **Safety scripts / entrypoints**:
    - `tools\Run-Phase5SafetySnapshot.ps1`
      (Block-G snapshot → RunContext → CSV → dashboard).
    - `tools\Show-Phase5SafetyState.ps1` (human-readable safety view).
    - `tools\Run-Phase5DailyPlaybook.ps1`
      - Step 0: safety snapshot.
      - Step 1: Phase-2→5 validation slice.
      - Step 2: GateScore daily pipeline.
      - Step 3: NVDA Block-G readiness checklist.
      - Step 4: safety dashboard.
    - `tools\Run-Phase5SafetyAudit.ps1`
      - Runs safety snapshot + NVDA/ SPY / QQQ gated pre-market wrappers.
    - `tools\Run-PreMarketOneTapGatedNvda.ps1`
      - Calls safety snapshot + `Check-BlockGReady.ps1 -Symbol NVDA`
        before the usual Phase-5 pre-market flow.
    - `tools\Run-SpyPhase5GatedPreMarket.ps1`,
      `tools\Run-QqqPhase5GatedPreMarket.ps1`
      - Same safety stack, but **Block-G correctly blocks** SPY/QQQ
        while their contracts are not ready.
- Contract (intent):
  - NVDA live can only be armed when:
    - Phase-4 validation harness passes for the current code.
    - Phase-2/3 health CSV is up to date.
    - EV-hard veto daily snapshot exists and is green.
    - GateScore daily summary is fresh and meets minimum sample counts.
    - `Check-BlockGReady.ps1 -Symbol NVDA` exits with code 0.
- Next:
  - Tune EV-bands and thresholds.
  - Harden Notion dashboards for EV vs realized PnL and Block-G status.
  - Define tiny-size live scaling rules under Block-G.

## Phase 6 – Strategy Expansion
- Status: **PLANNED.**
- Goal:
  - Add additional strategy families (e.g., scalper variants and new symbols).
  - Keep Block-G + RunContext + daily GateScore + EV-hard veto as mandatory
    pre-flight for any new live strategy.

## Phase 7 – Portfolio Optimizer
- Status: **PLANNED.**
- Goal:
  - Combine multiple Phase-5 strategies into a portfolio with position/risk limits.
  - Use EV + realized PnL histories, GateScore, and microstructure/cost metrics
    for allocation and scaling decisions.

---

This file is a living snapshot; update as you promote phases and strategies.