# Block-G Pre-Market Playbook (NVDA)

## Institutional Rule (FAIL-CLOSED)
NVDA live is **never armed** unless all strict-today gates are TRUE:
- Phase-4 passed today (`phase4_ok_today=true`)
- EV-hard veto passed today (`ev_hard_daily_ok_today=true`)
- GateScore is fresh today and passes thresholds (`gatescore_ok_today=true`)
- Block-G per-symbol ready flag true (`nvda_blockg_ready=true`)
- `tools\Check-BlockGReady.ps1 -Symbol NVDA` exits 0

If any gate fails: **FAIL-CLOSED** (no live orders).

## One-Command Pre-Market Run (06:45 PT)
```powershell
Set-Location C:\HAT
$ErrorActionPreference="Continue"; Set-StrictMode -Version Latest

.\tools\Run-PreMarketBlockG.ps1 -Symbol NVDA
"PREMARKET_BLOCKG_RC=$LASTEXITCODE" | Out-Host