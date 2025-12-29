[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)

# HARD paper-only safety (institutional fail-closed)
$env:HAT_IS_PAPER="1"
$env:HAT_LIVE_DISABLED="1"

# Require Notion env (fail-closed)
if([string]::IsNullOrWhiteSpace($env:NOTION_TOKEN)){
  $env:NOTION_TOKEN = [Environment]::GetEnvironmentVariable("NOTION_TOKEN","User")
}
if([string]::IsNullOrWhiteSpace($env:HAT_NOTION_PHASE6_DB_ID)){
  $env:HAT_NOTION_PHASE6_DB_ID = [Environment]::GetEnvironmentVariable("HAT_NOTION_PHASE6_DB_ID","User")
}
if([string]::IsNullOrWhiteSpace($env:NOTION_TOKEN)){ throw "Missing NOTION_TOKEN (User/Process)" }
if([string]::IsNullOrWhiteSpace($env:HAT_NOTION_PHASE6_DB_ID)){ throw "Missing HAT_NOTION_PHASE6_DB_ID (User/Process)" }

# Phase-6 state + CSV
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Run-Phase6OneTap.ps1")


# FAIL-CLOSED: propagate OneTap exit code (automation must see failure)
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
# Notion upsert by as_of_date
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Push-Phase6DailySummary-ToNotion.ps1")

# Print single-line result
$p = Get-Content -LiteralPath (Join-Path $repoRoot "logs\phase6_portfolio_state.json") -Raw -Encoding utf8 | ConvertFrom-Json
$ready = ""
if($null -ne $p.ready_symbols){ $ready = [string]::Join(",", @($p.ready_symbols)) }
Write-Host ("[PHASE6-ONETAP+NOTION] ok={0} reason={1} ready={2} as_of={3}" -f $p.ok, $p.reason, $ready, $p.as_of_date) -ForegroundColor Cyan

exit 0
