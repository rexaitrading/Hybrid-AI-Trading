[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $py)){ throw "python missing: $py" }

$bg = Join-Path $repoRoot "logs\blockg_status_stub.json"
if(-not (Test-Path $bg)){ throw "missing BlockG status: $bg" }

$env:HAT_BLOCKG_STATUS_PATH = $bg
& $py -m tools.smoke.smoke_assert_nvda_live_ready
$rc = $LASTEXITCODE
Remove-Item Env:HAT_BLOCKG_STATUS_PATH -ErrorAction SilentlyContinue

if($rc -ne 0){ throw "Smoke-AssertNvdaLiveReady FAILED rc=$rc" }
Write-Host "[SMOKE] OK assert_nvda_live_ready fail-closed confirmed" -ForegroundColor Green
exit 0
