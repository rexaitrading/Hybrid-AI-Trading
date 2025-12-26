[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)]
  [ValidateSet("paper-gateway","paper-tws","live-gateway","live-tws")]
  [string]$target
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$map = @{
  "paper-gateway" = ".env.paper.ibg"
  "paper-tws"     = ".env.paper.tws"
  "live-gateway"  = ".env.live.ibg"
  "live-tws"      = ".env.live"
}

if (-not $map.ContainsKey($target)) { throw "Unknown target: $target" }

$src = $map[$target]
if (-not (Test-Path -LiteralPath $src)) { throw "Config $src not found." }

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
if (Test-Path ".env") { Copy-Item -Force ".env" (".env.backup_" + $stamp) }

Copy-Item -Force $src ".env"

Write-Host (" Switched to {0} (contents suppressed for safety)." -f $target) -ForegroundColor Green
exit 0