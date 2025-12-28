[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)

"LOCAL=" + (Get-Date).ToString("yyyy-MM-dd HH:mm:ss") | Out-Host
"UTC  =" + (Get-Date).ToUniversalTime().ToString("o") | Out-Host
"" | Out-Host

$stamp = Join-Path $repoRoot "logs\daily_ops_onetap_last_ok.json"
if(Test-Path $stamp){
  "=== DAILY OPS STAMP ===" | Out-Host
  Get-Content -LiteralPath $stamp -Raw -Encoding utf8 | Out-Host
} else {
  "=== DAILY OPS STAMP ===" | Out-Host
  "MISSING: $stamp" | Out-Host
}
"" | Out-Host

$p6 = Join-Path $repoRoot "logs\phase6_portfolio_state.json"
if(Test-Path $p6){
  "=== PHASE6 STATE (key fields) ===" | Out-Host
  $o = Get-Content -LiteralPath $p6 -Raw -Encoding utf8 | ConvertFrom-Json
  ("as_of_date={0} ok={1} reason={2} ready={3} ts_utc={4}" -f $o.as_of_date,$o.ok,$o.reason,([string]::Join(",",@($o.ready_symbols))),$o.ts_utc) | Out-Host
} else {
  "=== PHASE6 STATE ===" | Out-Host
  "MISSING: $p6" | Out-Host
}
"" | Out-Host

"NOTION_TOKEN_PREFIX=" + $($env:NOTION_TOKEN.Substring(0,[Math]::Min(10,$env:NOTION_TOKEN.Length))) | Out-Host
"HAT_NOTION_PHASE6_DB_ID=" + $env:HAT_NOTION_PHASE6_DB_ID | Out-Host

exit 0

