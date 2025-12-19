# INVOKE_BLOCKGREADY_CHILD_ONLY
# This script MUST be launched as a child process:
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Invoke-BlockGReady.ps1 -Symbol ALL -Build
# Running it directly (.\tools\Invoke-BlockGReady.ps1) may terminate your ConsoleHost due to exit codes.
if ($MyInvocation.InvocationName -notlike "*powershell*") {
  Write-Host "[Invoke-BlockGReady] REFUSE: run as child process only. Use: powershell -File .\tools\Invoke-BlockGReady.ps1 ..." -ForegroundColor Yellow
  return 2
}
[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)]
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "ALL",

  [Parameter(Mandatory=$false)]
  [switch]$Build
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

# IMPORTANT:
# - Run-BlockGReady.ps1 returns an [int] in-session, and exits when run via -File.
# - Here we dot-NOT-source. We invoke it as a script and capture its return value.
$rc = & (Join-Path $repoRoot "tools\Run-BlockGReady.ps1") -Symbol $Symbol -Build:$Build
exit [int]$rc