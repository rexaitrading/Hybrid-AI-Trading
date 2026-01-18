[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market = "",

  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA"
)Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$root = (Resolve-Path ".").Path
Set-Location -LiteralPath $root

# Market/Symbol normalize (env-first) for per-market snapshot writes
$m = (($Market + "")).Trim().ToUpperInvariant()
if(-not $m){ $m = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant() }
if(-not $m){ $m = "US" }
$Market = $m

$s = (($Symbol + "")).Trim().ToUpperInvariant()
if(-not $s){ $s = (($env:HAT_SYMBOL + "")).Trim().ToUpperInvariant() }
if(-not $s){ $s = "NVDA" }
$Symbol = $s


# Ensure downstream builders see market/day (A3 single truth)
$env:HAT_MARKET = $Market
$env:HAT_SYMBOL = $Symbol
$asof = (($env:HAT_ASOF_DATE + "")).Trim()
if($asof){ $env:HAT_ASOF_DATE = $asof }
$logRoot = Join-Path (Join-Path $root "logs") $Market
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
# --- PER-MARKET EV-HARD OUTPUT PATHS (authoritative) ---
$dstEvidence = Join-Path $logRoot "ev_hard_snapshot.json"
  $dstRaw      = Join-Path $logRoot "ev_hard_evidence_raw.json"
$dstVeto     = Join-Path $logRoot "phase5_ev_hard_veto_snapshot.json"
# --- PER-MARKET EV-HARD OUTPUT PATHS END ---
$build   = Join-Path $root "tools\Build-EvHardSnapshot.ps1"
$compute = Join-Path $root "tools\Compute-Phase5EvHardSnapshotInput.ps1"
$export  = Join-Path $root "tools\Export-Phase5EvHardVetoDailySnapshot.ps1"


$rawBuild = Join-Path $root "tools\Build-EvHardEvidenceRaw.ps1"
if(-not (Test-Path $rawBuild)) { throw "[EV-HARD-SNAP] missing $rawBuild" }
if(-not (Test-Path $build))   { throw "[EV-HARD-SNAP] missing $build" }
if(-not (Test-Path $compute)) { throw "[EV-HARD-SNAP] missing $compute" }
if(-not (Test-Path $export))  { throw "[EV-HARD-SNAP] missing $export" }
  & $rawBuild -OutPath $dstRaw
if($LASTEXITCODE -ne 0){ throw "[EV-HARD-SNAP] Build-EvHardEvidenceRaw failed rc=$LASTEXITCODE" }


  & $build -EvidencePath $dstRaw -OutPath $dstEvidence
if($LASTEXITCODE -ne 0){ throw "[EV-HARD-SNAP] Build-EvHardSnapshot failed rc=$LASTEXITCODE" }

& $compute -EvidencePath $dstEvidence
if($LASTEXITCODE -ne 0){ throw "[EV-HARD-SNAP] Compute-Phase5EvHardSnapshotInput failed rc=$LASTEXITCODE" }

& $export
if($LASTEXITCODE -ne 0){ throw "[EV-HARD-SNAP] Export-Phase5EvHardVetoDailySnapshot failed rc=$LASTEXITCODE" }

$out = Join-Path $root "logs\phase5_ev_hard_veto_snapshot.json"
if(-not (Test-Path $out)){ throw "[EV-HARD-SNAP] snapshot not produced: $out" }
# Dual-write: copy root snapshots into per-market logRoot for market-aware consumers (fail-closed)
$rootEvidence = Join-Path $root "logs\ev_hard_snapshot.json"
$rootSnapVeto = Join-Path $root "logs\phase5_ev_hard_veto_snapshot.json"

if(-not (Test-Path -LiteralPath $rootEvidence)){ throw "[EV-HARD-SNAP] missing root evidence snapshot: $rootEvidence" }
if(-not (Test-Path -LiteralPath $rootSnapVeto)){ throw "[EV-HARD-SNAP] missing root veto snapshot: $rootSnapVeto" }
Copy-Item -LiteralPath $dstEvidence -Destination $rootEvidence -Force
Copy-Item -LiteralPath $rootSnapVeto -Destination $dstVeto -Force

Write-Host ("[EV-HARD-SNAP] copied => " + $dstEvidence) -ForegroundColor Green
Write-Host ("[EV-HARD-SNAP] copied => " + $dstVeto) -ForegroundColor Green

Write-Host "[EV-HARD-SNAP] OK wrote $out" -ForegroundColor Green
# [A2] refresh ev_hard_status.json (market-aware) after snapshots are in-place
$st = Join-Path $root "tools\Build-EvHardStatus.ps1"
if(-not (Test-Path -LiteralPath $st)){ throw "[EV-HARD-SNAP] missing status writer: $st" }
& $st -Market $Market
if($LASTEXITCODE -ne 0){ throw "[EV-HARD-SNAP] Build-EvHardStatus failed rc=$LASTEXITCODE" }
exit 0
