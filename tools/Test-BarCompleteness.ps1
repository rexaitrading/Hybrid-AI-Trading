[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",
  [string]$BarsPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Stub: user must point BarsPath to the replay bars file (csv/jsonl/parquet).
# Institutional rule: missing/duplicate timestamps => fail (exit 2).
if(-not $BarsPath){ throw "BarsPath required (point to replay bars artifact)" }
if(-not (Test-Path -LiteralPath $BarsPath)){ throw "Missing BarsPath: $BarsPath" }

# TODO: implement timestamp uniqueness + expected bar count by session.
"[BAR-CHECK] OK_STUB symbol=$Symbol path=$BarsPath" | Out-Host
exit 0
