# scripts\run_ibg_daily.ps1
# BUILD: daily-wrapper-v3 (path-robust, PS 5.1 safe)
$ErrorActionPreference = "Stop"

# Resolve this script's folder reliably (works in Task Scheduler)
$scriptPath = $MyInvocation.MyCommand.Path
$scriptDir  = if ($scriptPath) { Split-Path -Parent $scriptPath } else { (Get-Location).Path }

# Repo root = parent of 'scripts' if applicable; else current location
if ((Split-Path -Leaf $scriptDir) -ieq 'scripts') {
  $repoRoot = Resolve-Path (Join-Path $scriptDir '..')
} else {
  $repoRoot = (Get-Location).Path
}

# Use repo root as working directory so relative paths resolve
Set-Location -Path $repoRoot

# Find the one-shot preflight script
$oneShot = Join-Path $scriptDir 'ibg_start_preflight_and_test.ps1'
if (-not (Test-Path $oneShot)) { $oneShot = Join-Path $repoRoot 'scripts\ibg_start_preflight_and_test.ps1' }
if (-not (Test-Path $oneShot)) {
  $hit = Get-ChildItem -Path $repoRoot -Filter 'ibg_start_preflight_and_test.ps1' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($hit) { $oneShot = $hit.FullName }
}
if (-not (Test-Path $oneShot)) {
  throw "One-shot script not found. Tried:
  - $scriptDir\ibg_start_preflight_and_test.ps1
  - $repoRoot\scripts\ibg_start_preflight_and_test.ps1
  - plus recursive search under $repoRoot"
}

Write-Host ("Using one-shot: {0}" -f $oneShot) -ForegroundColor Cyan

# Transcript in your home folder
$log = Join-Path $env:USERPROFILE ("ibg_daily_{0}.log" -f (Get-Date -Format 'yyyyMMdd_HHmm'))
Start-Transcript -Path $log -NoClobber
try {
  # start → wait → handshake → test
  powershell -NoProfile -ExecutionPolicy Bypass -File $oneShot
}
finally {
  Stop-Transcript
}