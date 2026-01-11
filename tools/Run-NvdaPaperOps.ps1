[CmdletBinding()]
param(
  [int]$MinEvents = 25
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
# --- FORCE CANONICAL REPO ROOT (stable; avoids OneDrive "??" view) ---
$repoRoot = & (Join-Path $PSScriptRoot "Go-RepoRoot.ps1")
if(-not $repoRoot){ throw "[OPS] Go-RepoRoot returned empty" }
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot
Write-Host ("[OPS] CANON_REPO_ROOT=" + $repoRoot) -ForegroundColor DarkGray
# ---------------------------------------------------------------

Write-Host "[OPS] 1) Merge tick files -> stream" -ForegroundColor Cyan
$mergeArgs = @{ LocalOutDir = "C:\Trading\tmp" }
& (Join-Path $repoRoot "tools\Merge-NvdaPaperTicks.ps1") @mergeArgs
if($LASTEXITCODE -ne 0){ throw ("[OPS] merge failed rc=" + $LASTEXITCODE) }
Write-Host "[OPS] 2) Rebuild NVDA GateScore events from stream" -ForegroundColor Cyan
$stream = ".\logs\nvda_paperlive_stream_today.jsonl"
if(-not (Test-Path $stream)){ throw "[OPS] missing stream: $stream" }
& .\tools\Write-NvdaGateScoreEventsFromPaperlive.ps1 -InputPath $stream -Mode rewrite -MinEvents $MinEvents
if($LASTEXITCODE -ne 0){ throw "[OPS] gatescore events failed rc=$LASTEXITCODE" }

Write-Host "[OPS] 3) Summaries" -ForegroundColor Cyan
& .\tools\Build-GateScorePnlSummary.ps1 -Symbol NVDA -StrictToday
if($LASTEXITCODE -ne 0){ throw "[OPS] pnl summary failed rc=$LASTEXITCODE" }
& .\tools\Build-GateScoreDailySummary.ps1
if($LASTEXITCODE -ne 0){ throw "[OPS] daily summary failed rc=$LASTEXITCODE" }

Write-Host "[OPS] 4) EV-hard snapshot" -ForegroundColor Cyan
& .\tools\Build-EvHardEvidenceRaw.ps1
if($LASTEXITCODE -ne 0){ throw "[OPS] evhard evidence failed rc=$LASTEXITCODE" }
& .\tools\Build-EvHardSnapshot.ps1
if($LASTEXITCODE -ne 0){ throw "[OPS] evhard snapshot failed rc=$LASTEXITCODE" }
& .\tools\Write-EvHardVetoSnapshot.ps1
if($LASTEXITCODE -ne 0){ throw "[OPS] evhard veto snapshot failed rc=$LASTEXITCODE" }
& .\tools\Run-EvHardVetoDaily.ps1
if($LASTEXITCODE -ne 0){ throw "[OPS] evhard daily failed rc=$LASTEXITCODE" }

Write-Host "[OPS] 5) BlockG rebuild + check (NVDA)" -ForegroundColor Cyan
& .\tools\Build-BlockGStatusStub.ps1 -Symbol NVDA
& .\tools\Check-BlockGReady.ps1 -Symbol NVDA
if($LASTEXITCODE -ne 0){ throw "[OPS] BlockG not ready rc=$LASTEXITCODE" }

Write-Host "[OPS] OK: NVDA paper ops green" -ForegroundColor Green
exit 0