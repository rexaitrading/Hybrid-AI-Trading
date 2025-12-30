[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsDir  = Join-Path $repoRoot "logs"

"=== Build Block-G contract ===" | Out-Host
& (Join-Path $toolsDir "Build-BlockGStatusStub.ps1") -Symbol $Symbol | Out-Host

"=== Export Notion CSV ===" | Out-Host
$exporter = Join-Path $toolsDir "Export-BlockGReadinessForNotion.ps1"
& $exporter | Out-Host

$csvPath = Join-Path $logsDir "blockg_readiness_for_notion.csv"
if(-not (Test-Path -LiteralPath $csvPath)){ throw "Missing CSV: $csvPath" }

$j = Get-Content (Join-Path $logsDir "blockg_status_stub.json") -Raw -Encoding utf8 | ConvertFrom-Json
"as_of_date=$($j.as_of_date) gatescore_as_of_date=$($j.gatescore_as_of_date)" | Out-Host
"nvda_blockg_ready=$($j.nvda_blockg_ready) spy_blockg_ready=$($j.spy_blockg_ready) qqq_blockg_ready=$($j.qqq_blockg_ready)" | Out-Host
"CSV=$csvPath" | Out-Host
exit 0
