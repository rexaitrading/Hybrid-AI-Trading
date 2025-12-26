[CmdletBinding()]
param(
  [string]$Symbol = "NVDA",
  [string]$Regime = "PHASE1_REPLAY_TO_FORWARD",
  [string]$Mode   = "paper",
  [string]$Phase1HashCsv = ""
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$root = (Resolve-Path ".").Path
$dir  = Join-Path $root "logs\run_journal"
New-Item -ItemType Directory -Force -Path $dir | Out-Null

$ts   = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
$day  = (Get-Date).ToString("yyyy-MM-dd")
$runId = "RUN_" + (Get-Date -Format "yyyyMMdd_HHmmss")

# JSON template (ordered for diff stability)
$obj = [ordered]@{
  run_id = $runId
  date   = $day
  ts     = $ts

  symbol = $Symbol
  regime = $Regime
  mode   = $Mode

  # Phase-1
  phase1_replay_ok = $true
  phase1_hash_csv  = $Phase1HashCsv

  # Phase-2 (filled later by micro snapshot)
  phase2_micro_snapshot_ok = $false
  est_slippage_pct   = $null
  est_latency_ms     = $null
  est_total_cost_pct = $null

  # Phase-3 (filled later by daily_build)
  gatescore_ok_today = $false
  gatescore_value    = $null
  gatescore_samples  = $null

  # Phase-4/5/Block-G (filled later by preflight)
  phase4_ok_today        = $false
  ev_hard_ok_today       = $false
  blockg_ready_symbol    = $false
  blockg_status_path     = ""

  # Trading journal (you fill)
  planned_setups  = @()
  executed_trades = @()
  notes = ""
}

$jsonPath = Join-Path $dir ("run_journal_" + $runId + ".json")
$csvPath  = Join-Path $dir ("run_journal_" + $runId + ".csv")

$obj | ConvertTo-Json -Depth 10 | Out-File -LiteralPath $jsonPath -Encoding utf8 -Force
([PSCustomObject]$obj) | Export-Csv -NoTypeInformation -Encoding utf8 -LiteralPath $csvPath -Force

Write-Host "WROTE_JSON=$jsonPath" -ForegroundColor Green
Write-Host "WROTE_CSV=$csvPath" -ForegroundColor Green
exit 0