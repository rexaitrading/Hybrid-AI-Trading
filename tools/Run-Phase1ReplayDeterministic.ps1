[CmdletBinding()]
param(
  [string]$Symbol = "NVDA",
  [string]$Regime = "PHASE1_REPLAY_TO_FORWARD",
  [switch]$ExportNotion,
  [switch]$KeepArtifacts
)


# --- repo root bootstrap (env-first) ---
$repoRoot = ($env:HAT_REPO_ROOT + "").Trim()
if(-not $repoRoot){
  $repoRoot = & (Join-Path $PSScriptRoot "Go-RepoRoot.ps1")
}
if(-not $repoRoot){ throw "[REPOROOT] FAIL-CLOSED: repoRoot empty (env+Go-RepoRoot)" }
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
# $root = (Resolve-Path ".").Path                 # disabled (use env HAT_REPO_ROOT)
$logs = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null

# Determinism knobs
$env:PYTHONNOUSERSITE  = "1"
$env:PYTHONHASHSEED    = "0"
$env:HAT_DETERMINISTIC = "1"

# Artifact dir
$art = Join-Path $logs "phase1_artifacts"
if(-not $KeepArtifacts){
  if(Test-Path $art){ Remove-Item -Recurse -Force $art }
}
New-Item -ItemType Directory -Force -Path $art | Out-Null

Write-Host "[PHASE1] ROOT=$root" -ForegroundColor Cyan
Write-Host "[PHASE1] ARTIFACT_DIR=$art" -ForegroundColor Cyan

# Run suite (single source of truth)
$suite = Join-Path $root "tools\Run-Phase1ReplaySuite.ps1"
if(-not (Test-Path $suite)){ throw "Missing $suite" }
& $suite
if($LASTEXITCODE -ne 0){ throw "Phase1 suite failed exit=$LASTEXITCODE" }

# Determinism proof (Phase-1 only): hash replay_summary_*.json in repo root and logs (if any)
$sum1 = Get-ChildItem $root -File -Filter "replay_summary_*.json" -ErrorAction SilentlyContinue
  # BOUNDED: do not recurse all logs/ (polluted by non-market folders). Only scan canonical market folder.
  $sum2 = @()
  try {
    $m = ([string]$Market).ToUpperInvariant().Trim()
    if(-not $m){ $m = "US" }
    $pMkt = Join-Path $logs $m
    if(Test-Path -LiteralPath $pMkt){
      $sum2 = @(Get-ChildItem -LiteralPath $pMkt -File -Filter "replay_summary_*.json" -ErrorAction SilentlyContinue)
    }
  } catch { $sum2 = @() }
$targets = @($sum1 + $sum2) | Sort-Object FullName -Unique

$hashes = foreach($f in $targets){
  try {
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath $f.FullName).Hash
    [PSCustomObject]@{ File = $f.FullName.Substring($root.Length+1); Sha256=$h; HashError="" }
  } catch {
    [PSCustomObject]@{ File = $f.FullName.Substring($root.Length+1); Sha256=""; HashError=$_.Exception.Message }
  }
}

$hashPath = Join-Path $art ("phase1_hashes_" + (Get-Date -Format yyyyMMdd_HHmmss) + ".csv")
$hashes | Export-Csv -NoTypeInformation -Encoding utf8 $hashPath
Write-Host "[PHASE1] HASHES_WRITTEN=$hashPath" -ForegroundColor Green

# Journal template (replay -> forward play)
$jt = Join-Path $root "tools\Write-RunJournalTemplate.ps1"
if(Test-Path $jt){
  & $jt -Symbol $Symbol -Regime $Regime -Mode "paper" -Phase1HashCsv $hashPath
}

# Optional Notion export (uses your existing exporter if present)
if($ExportNotion){
  $exporter = Join-Path $root "tools\Run-ExportNvdaGateScoreForNotion.ps1"
  if(Test-Path $exporter){
    & $exporter
    if($LASTEXITCODE -ne 0){ throw "Notion exporter failed exit=$LASTEXITCODE" }
    Write-Host "[PHASE1] NOTION_EXPORT_OK via $exporter" -ForegroundColor Green
  } else {
    Write-Warning "[PHASE1] ExportNotion requested but exporter not found: $exporter"
  }
}

exit 0
