# Phase Roadmap – Snapshot (2025-12-09)

## Phase 1 – Bar Replay / Research Harness
- Status: **IN PROGRESS** (branch: `feature/phase1-bar-replay`)
- Goal:
  - Stable bar-replay to JSONL/CSV.
  - Easy walk-forward and EV/gap sweep for NVDA/SPY/QQQ.
- Next:
  - Finish remaining tests and CI wiring.
  - Merge into main once fully green.

## Phase 2 – Microstructure + Cost Model
- Status: **ACTIVE (SPY/QQQ ORB micro + cost)**.
- Artifacts:
  - `logs\spy_phase5_paper_for_notion_ev_diag_micro.csv`
  - `logs\qqq_phase5_paper_for_notion_ev_diag_micro.csv`
  - `logs\spy_qqq_micro_for_notion.csv`
- Next:
  - Feed spread/fee estimates into Phase-5 risk sizing.

## Phase 3 – GateScore Engine
- Status: **ACTIVE (NVDA GateScore replay + summaries)**.
- Artifacts:
  - `logs\gatescore_pnl_summary.csv`
  - `tools\gatescore.py`, `tools\replay_gatescore.py` (pipeline).
- Next:
  - Stronger daily GateScore pipeline; Notion dashboards for GateScore vs realized PnL.

## Phase 4 – Validation Harness
- Status: **WIRED INTO Run-BlockGReadiness**.
- Steps:
  - Phase-2 dry-run + snapshot.
  - Phase-2/3 quick diagnostics (Run-Phase23Quick).
  - Phase-5 risk microsuite (27 tests).
- Next:
  - Keep this stable as we add more strategies.

## Phase 5 – Controlled Live (NVDA_BPLUS_LIVE + SPY_ORB_LIVE + QQQ_ORB_LIVE)
- Status: **SAFETY STACK GREEN; TRADING WINDOW GATED**.
- Safety layers:
  - Block-G contract (blockg_status_stub.json)
  - RunContext (run_context_stub.json)
  - SAFE-RESUME (Run-Phase5SafeResume.ps1)
  - Pre-market gating (Run-PreMarketOneTap.ps1 + Check-BlockGReady.ps1)
- Next:
  - Tune EV-bands, Notion dashboards, and tiny-size live scaling rules.

## Phase 6 – Strategy Expansion
- Status: **PLANNED**.
- Goal:
  - Add additional strategy families (e.g., scalper variants, other symbols).
  - Keep Block-G + RunContext + SAFE-RESUME as mandatory pre-flight.

## Phase 7 – Portfolio Optimizer
- Status: **PLANNED**.
- Goal:
  - Combine multiple Phase-5 strategies into a portfolio with position/risk limits.
  - Use EV + realized PnL histories for allocation and scaling decisions.

---
This file is a living snapshot; update as you promote phases and strategies.