[CmdletBinding()]
param(
  [string]$StatusPath = ".\logs\blockg_status_stub.json",
  [string]$OutCsv = ".\logs\blockg_daily_for_notion.csv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

if (-not (Test-Path $StatusPath)) { throw "StatusPath missing: $StatusPath" }

$j = Get-Content $StatusPath -Raw -Encoding utf8 | ConvertFrom-Json

# Ensure header once
if (-not (Test-Path $OutCsv)) {
  "as_of_date,nvda_ready,spy_ready,qqq_ready,phase23_ok,phase4_ok,ev_hard_ok,gatescore_ok,reasons,market_closed_today,ev_hard_daily_as_of_date,ev_hard_session_as_of_date,gatescore_as_of_date,gatescore_samples,gatescore_ok_live_today" |
    Out-File -LiteralPath $OutCsv -Encoding utf8
}

$reasons = ""
try { $reasons = (($j.reasons_not_ready | ForEach-Object { $_ }) -join "|") } catch { $reasons = "" }

$row = '{0},{1},{2},{3},{4},{5},{6},{7},"{8}",{9},"{10}","{11}","{12}",{13},{14}' -f `
  $j.as_of_date, $j.nvda_blockg_ready, $j.spy_blockg_ready, $j.qqq_blockg_ready, `
  $j.phase23_health_ok_today, $j.phase4_ok_today, $j.ev_hard_daily_ok_today, $j.gatescore_ok_today, $reasons, `
  $j.market_closed_today, $j.ev_hard_daily_as_of_date, $j.ev_hard_session_as_of_date, $j.gatescore_as_of_date, ([int]($j.gatescore_samples + 0)), ([bool]$j.gatescore_ok_live_today)

# Remove existing today row (idempotent)
$today = [string]$j.as_of_date
$rows = Get-Content -LiteralPath $OutCsv -Encoding utf8 | Where-Object { $_ -and ($_ -notmatch "^\s*$today,") }
$rows | Out-File -LiteralPath $OutCsv -Encoding utf8 -Force
$row  | Add-Content -LiteralPath $OutCsv -Encoding utf8

Write-Host "[NOTION] wrote $OutCsv date=$today" -ForegroundColor Green
exit 0
