# Phase-5 CI / Microsuite Specification

This document defines the **required CI checks** for Phase-5 readiness.

## 1. Phase-5 Microsuite

Entry point:

- `tools\Run-Phase5MicroSuite.ps1`
- Config: `config\phase5\ci_microsuite.txt`

Typical contents (subject to change):

- `tools\test_phase5_live_runners.py`
- `tools\test_phase5_place_order_wrapper.py`
- `tools\test_phase5_no_averaging_hook.py`
- `tools\test_phase5_no_averaging_adapter_positions.py`
- `tools\test_paper_exec_logger.py`
- `tools\test_notion_hybrid_snapshot.py`
- `tests\test_phase5_account_caps_integration.py`
- `tests\test_phase5_account_daily_caps.py`
- `tests\test_phase5_daily_loss_gate.py`
- `tests\test_phase5_engine_guard.py`
- `tests\test_phase5_ev_bands_basic.py`
- `tests\test_phase5_ev_band_hard_veto.py`
- `tests\test_phase5_no_averaging_engine_guard.py`
- `tests\test_phase5_no_avg_gate.py`
- `tests\test_phase5_policy.py`
- `tests\test_phase5_riskmanager_combined_gates.py`
- `tests\test_phase5_riskmanager_daily_loss_integration.py`
- `tests\test_phase5_risk_adapter_stub.py`
- `tests\test_phase5_risk_cli_tools.py`
- `tests\test_phase5_risk_policy.py`
- `tests\test_phase5_wiring_sim.py`

**All microsuite tests must be green** before:

- Marking a Phase-5 config as live ready.
- Running PreMarket-Check / PreMarket-OneTap for live capital.

## 2. EV Preflight

Entry point:

- `tools\Run-Phase5EvPreflight.ps1`

Steps:

1. `Show-Phase5EvAnchors.ps1` — NVDA/SPY/QQQ EV models + EV-bands.
2. `Run-Phase5Audit.ps1` — NVDA/SPY/QQQ Phase-5 PnL/EV audit.
3. Pytest slice:
   - `tests\test_phase5_riskmanager_combined_gates.py`
   - `tests\test_phase5_riskmanager_daily_loss_integration.py`
   - `tests\test_phase5_no_averaging_engine_guard.py`
   - `tests\test_phase5_ev_bands_basic.py`
   - `tests\test_phase5_ev_band_hard_veto.py`
   - `tests\test_execution_engine_phase5_guard.py`
   - `tests\test_ib_phase5_guard.py`

**All EV preflight tests must be green** before live sessions.

## 3. Pre-Market Integration

- `tools\PreMarket-Check.ps1`:
  - Runs Phase-5 microsuite gate.
  - Runs `Run-Phase5EvPreflight.ps1` as **STEP 0**.
  - Runs Python pre-market risk + QoS checks.

- `tools\PreMarket-OneTap.ps1`:
  - Runs `Run-Phase5EvPreflight.ps1` as **STEP 0**.
  - Runs Phase-5 microsuite gate.
  - Runs Phase-5 EV sync / EV hard-veto daily snapshot.

## 4. Live Readiness Rule (high-level)

A Phase-5 config can be considered **live-ready** when:

1. Phase-5 microsuite is fully green.
2. EV preflight is fully green.
3. PreMarket-Check.ps1 reports `OK_TO_TRADE`.
4. EV hard-veto daily snapshot and Notion AAR views for NVDA/SPY/QQQ show no anomalies.

Details will be refined in subsequent docs (e.g., Phase-5 Live Playbook).