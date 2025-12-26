# BlockG NVDA Live Arming Runbook

This runbook defines institutional **NVDA LIVE READY** and the exact PowerShell commands to **Arm** and **Disarm** live trading (fail-closed).

## Definition: NVDA LIVE READY
NVDA is allowed to send live orders only if ALL are true:

- Phase4 stamp is OK today (UTC): `logs/phase4_validation_passed.json`
- GateScore daily summary is today-only and fresh today (UTC): `logs/gatescore_daily_summary.csv`
- BlockG contract is built for today and reports `nvda_blockg_ready=true`: `logs/blockg_status_stub.json`
- `Check-BlockGReady.ps1 -Symbol NVDA` exits 0
- NVDA Live Stamp is today and `nvda_live_ready=true` (human consent): `logs/nvda_live_ready_stamp.json`
- Python live order path is defense-in-depth gated:
  - ExecutionEngine
  - OrderManager
  - IB chokepoint

## Arm NVDA Live (fail-closed)
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Arm-NVDA-Live.ps1
echo "arm_exit=$LASTEXITCODE"
Get-Content .\logs\nvda_live_ready_stamp.json -Raw -Encoding utf8