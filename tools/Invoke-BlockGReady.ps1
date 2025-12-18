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