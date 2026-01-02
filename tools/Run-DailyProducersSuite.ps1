[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = (Resolve-Path ".").Path
Set-Location $root

function Run-Step([string]$Name, [string]$Script){
  if(-not (Test-Path -LiteralPath $Script)){
    throw "[DAILY] Missing step script: $Script"
  }

  Write-Host ("[DAILY] RUN " + $Name + " -> " + $Script) -ForegroundColor Cyan
  powershell -NoProfile -ExecutionPolicy Bypass -File $Script
  $rc = $LASTEXITCODE
  Write-Host ("[DAILY] DONE " + $Name + " exit=" + $rc) -ForegroundColor Yellow

  if($rc -ne 0){
    # Fail-soft: any Stamp* step can legitimately return rc=2 when Block-G is not ready (arming denied).
    if(($Name -like "Stamp*") -and ($rc -eq 2)){
      Write-Host "[DAILY] Stamp denied (rc=2) - Block-G not ready (expected). Continuing." -ForegroundColor Yellow
      return
    }
    throw "[DAILY] Step failed: $Name rc=$rc"
  }
}

# ---- Phase4 (validation stamp) ----
Run-Step "Phase4Stamp" ".\tools\Run-Phase4Stamp.ps1"

# ---- Phase23 (repo health) ----
Run-Step "Phase23HealthDaily" ".\tools\Run-Phase23HealthDaily.ps1"

# ---- Phase3 (GateScore summaries) ----
Run-Step "GateScorePnlSummary" ".\tools\Build-GateScorePnlSummary.ps1"
Run-Step "GateScoreDailySummary" ".\tools\Build-GateScoreDailySummary.ps1"

# ---- EV-HARD evidence (raw inputs) ----
Run-Step "EvHardEvidenceRaw" ".\tools\Build-EvHardEvidenceRaw.ps1"

# ---- BlockG contract ----
Run-Step "BlockGStatusStub" ".\tools\Build-BlockGStatusStub.ps1"

# ---- Symbol stamps ----
Run-Step "StampNVDA" ".\tools\Write-NvdaLiveReadyStamp.ps1"
Run-Step "SanitizeNVDAStamp" ".\tools\Sanitize-NvdaLiveReadyStamp.ps1"
Run-Step "StampSPY" ".\tools\Write-SpyLiveReadyStamp.ps1"
Run-Step "StampQQQ" ".\tools\Write-QqqLiveReadyStamp.ps1"

# ---- Notion payloads ----
Run-Step "NotionNVDA" ".\tools\Build-NotionNvdaLiveAllowedPayload.ps1"
Run-Step "NotionSPY"  ".\tools\Build-NotionSpyLiveAllowedPayload.ps1"
Run-Step "NotionQQQ"  ".\tools\Build-NotionQqqLiveAllowedPayload.ps1"

# ---- Phase6 snapshot (optional but recommended) ----
if(Test-Path -LiteralPath ".\tools\Build-Phase6PortfolioState.ps1"){
  Run-Step "Phase6PortfolioState" ".\tools\Build-Phase6PortfolioState.ps1"
}

Write-Host "[DAILY] ALL GREEN" -ForegroundColor Green
exit 0
