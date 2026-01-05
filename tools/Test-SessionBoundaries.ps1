[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",
  [string]$BarsPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if(-not $BarsPath){ throw "BarsPath required" }
if(-not (Test-Path -LiteralPath $BarsPath)){ throw "Missing BarsPath: $BarsPath" }

# TODO: implement pre/RTH/post tagging based on America/New_York session times.
"[SESSION-CHECK] OK_STUB symbol=$Symbol path=$BarsPath" | Out-Host
exit 0
