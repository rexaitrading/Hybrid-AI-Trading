[CmdletBinding()]
param(
  # Put your real live command here when ready (example shown)
  [string]$LiveCommand = ".\.venv\Scripts\python.exe .\src\hybrid_ai_trading\runners\nvda_phase5_live_runner.py"
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot
$env:PYTHONPATH = Join-Path $repoRoot "src"

$today = (Get-Date).ToString("yyyy-MM-dd")
$stamp = Get-Date -Format yyyyMMdd_HHmmss

Write-Host "[GO-ONLY] repo=$repoRoot today=$today" -ForegroundColor Cyan

# 0) Explicit human arming flag (prevents accidental live)
if (("$env:HAT_LIVE_ARM" -ne "1") -and ("$env:HAT_LIVE_ARM" -ne "true")) {
  Write-Host "[GO-ONLY] FAIL-CLOSED: set HAT_LIVE_ARM=1 to run live runner" -ForegroundColor Red
  exit 90
}

# 1) Refuse to run if IBC_INI looks like paper
$ini = "$env:IBC_INI"
if ([string]::IsNullOrWhiteSpace($ini)) {
  Write-Host "[GO-ONLY] FAIL-CLOSED: IBC_INI not set" -ForegroundColor Red
  exit 91
}
if ($ini.ToLowerInvariant().Contains("paper")) {
  Write-Host "[GO-ONLY] FAIL-CLOSED: IBC_INI indicates PAPER: $ini" -ForegroundColor Red
  exit 92
}

# 2) Run preflight (must be GO)
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Run-NvdaBlockGPreflight.ps1
if ($LASTEXITCODE -ne 0) {
  Write-Host "[GO-ONLY] NO-GO: preflight exitcode=$LASTEXITCODE" -ForegroundColor Red
  exit $LASTEXITCODE
}

# 3) Hash contract (must remain unchanged through run)
$contract = Join-Path $repoRoot "logs\blockg_status_stub.json"
if (-not (Test-Path $contract)) { Write-Host "[GO-ONLY] FAIL-CLOSED: missing $contract" -ForegroundColor Red; exit 93 }
$h0 = (Get-FileHash $contract -Algorithm SHA256).Hash

Start-Transcript -Path (Join-Path $repoRoot "logs\transcript_nvda_live_$stamp.txt") | Out-Null

try {
  Write-Host "[GO-ONLY] RUN: $LiveCommand" -ForegroundColor Yellow
  # Execute command line safely
  cmd.exe /c $LiveCommand
  $rc = $LASTEXITCODE
  Write-Host "[GO-ONLY] live runner exitcode=$rc" -ForegroundColor Cyan
} finally {
  Stop-Transcript | Out-Null
}

$h1 = (Get-FileHash $contract -Algorithm SHA256).Hash
if ($h1 -ne $h0) {
  Write-Host "[GO-ONLY] FAIL-CLOSED: contract changed during run hash0=$h0 hash1=$h1" -ForegroundColor Red
  exit 94
}

Copy-Item -Force $contract (Join-Path $repoRoot "logs\blockg_status_stub_USED_FOR_LIVE_$stamp.json")
Write-Host "[GO-ONLY] DONE: contract locked and snapshotted" -ForegroundColor Green
exit 0
