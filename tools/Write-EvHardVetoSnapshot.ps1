[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$root = (Resolve-Path ".").Path
Set-Location $root

$build   = Join-Path $root "tools\Build-EvHardSnapshot.ps1"
$compute = Join-Path $root "tools\Compute-Phase5EvHardSnapshotInput.ps1"
$export  = Join-Path $root "tools\Export-Phase5EvHardVetoDailySnapshot.ps1"

if(-not (Test-Path $build))   { throw "[EV-HARD-SNAP] missing $build" }
if(-not (Test-Path $compute)) { throw "[EV-HARD-SNAP] missing $compute" }
if(-not (Test-Path $export))  { throw "[EV-HARD-SNAP] missing $export" }

& $build
if($LASTEXITCODE -ne 0){ throw "[EV-HARD-SNAP] Build-EvHardSnapshot failed rc=$LASTEXITCODE" }

& $compute -EvidencePath ".\logs\ev_hard_snapshot.json"
if($LASTEXITCODE -ne 0){ throw "[EV-HARD-SNAP] Compute-Phase5EvHardSnapshotInput failed rc=$LASTEXITCODE" }

& $export
if($LASTEXITCODE -ne 0){ throw "[EV-HARD-SNAP] Export-Phase5EvHardVetoDailySnapshot failed rc=$LASTEXITCODE" }

$out = Join-Path $root "logs\phase5_ev_hard_veto_snapshot.json"
if(-not (Test-Path $out)){ throw "[EV-HARD-SNAP] snapshot not produced: $out" }

Write-Host "[EV-HARD-SNAP] OK wrote $out" -ForegroundColor Green
exit 0