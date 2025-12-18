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

$ps = (Get-Command powershell).Source

$args = @("-NoProfile","-ExecutionPolicy","Bypass","-File", (Join-Path $repoRoot "tools\Run-BlockGReady.ps1"), "-Symbol", $Symbol)
if ($Build) { $args += "-Build" }

& $ps @args
exit $LASTEXITCODE