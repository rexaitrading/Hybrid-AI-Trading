# Phase-5 Block-G Policy

## Purpose
Block-G is the institutional, fail-closed contract that decides whether a symbol may be armed for LIVE order submission.

**Rule:** A LIVE order must never bypass Block-G in the Python order path.

## Contract inputs (daily)
Block-G evaluates readiness from artifacts generated today:

1. Phase-4 validation stamp
   - logs/phase4_validation_passed.json
   - must be today and phase4_ok_today=true

2. Phase23 health (today-ness)
   - logs/phase23_health_daily.csv
   - must contain a row for today (date=YYYY-MM-DD)

3. EV-hard veto (today-ness)
   - logs/phase5_ev_hard_veto_daily.csv
   - must contain a row for today (date=YYYY-MM-DD)

4. GateScore daily summary (quality + freshness)
   - logs/gatescore_daily_summary_<symbol>.csv
   - must contain a row for today where source=REAL
   - must satisfy thresholds from docs/thresholds/gatescore_thresholds.psd1

## GateScore thresholds
Thresholds are policy, not plumbing. They prevent arming LIVE on thin/noisy data.

File: docs/thresholds/gatescore_thresholds.psd1

Fields:
- min_signals: minimum count_signals today
- min_pnl_samples: minimum pnl_samples today
- min_edge_ratio: absolute edge ratio threshold
- min_micro_score: minimum microstructure score

## Modes
- DEV_REPLAY: wiring stage only (must not arm LIVE)
- REAL: required for arming LIVE (Block-G freshness gate)

## Per-symbol contracts
Block-G writes per-symbol contract JSON files to prevent cross-symbol clobbering:

- logs/blockg_status_stub_nvda.json
- logs/blockg_status_stub_spy.json
- logs/blockg_status_stub_qqq.json

tools/Check-BlockGReady.ps1 -Symbol <X> reads the per-symbol file first (legacy fallback supported).

## Operator daily sequence (NVDA)
1) Phase-4 harness:
- powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Run-Phase4Validation.ps1

2) Produce today rows:
- powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Write-Phase23HealthToday.ps1 -Ok true
- powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Write-Phase5EvHardVetoToday.ps1 -Ok true

3) GateScore REAL:
- powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-GateScoreDailySummary.ps1 -Symbol NVDA -Mode REAL

4) Build & check contract:
- powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-BlockGStatusStub.ps1 -Symbol NVDA
- powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Check-BlockGReady.ps1 -Symbol NVDA

5) Python enforcement smoke:
- .\.venv\Scripts\python .\tools\smoke\smoke_blockg_contract_enforcement.py

## Policy note: SPY / QQQ
SPY and QQQ remain fail-closed until their GateScore REAL rows meet thresholds (signals, pnl samples, edge, micro).
This is expected and desirable until calibration is complete.