[CmdletBinding()]
param()

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

function Get-TodayStr { (Get-Date).ToString("yyyy-MM-dd") }

function Read-JsonSafe([string]$p) {
  if (-not (Test-Path $p)) { return $null }
  $raw = Get-Content $p -Raw -Encoding utf8
  if ($raw.Length -gt 0 -and [int][char]$raw[0] -eq 65279) { $raw = $raw.TrimStart([char]65279) }
  try { return ($raw | ConvertFrom-Json -ErrorAction Stop) } catch { return $null }
}

function Try-LoadCsv([string]$p) {
  if (-not (Test-Path $p)) { return @() }
  try { return @(Import-Csv $p) } catch { return @() }
}

function Has-TodayRow($rows, [string]$dateField, [string]$today) {
  foreach ($r in @($rows)) {
    if ($null -eq $r) { continue }
    $v = $r.$dateField
    if ($null -eq $v) { continue }
    $s = "$v"
    if ($s.Length -ge 10) { $s = $s.Substring(0,10) }
    if ($s -eq $today) { return $true }
  }
  return $false
}

function Get-GateScoreThresholds([string]$sym) {
  $p = "docs\thresholds\gatescore_thresholds.psd1"
  if (-not (Test-Path $p)) { return $null }
  $th = Import-PowerShellDataFile -Path $p
  $cfg = $th[$sym]
  if (-not $cfg) { $cfg = $th["DEFAULT"] }
  return $cfg
}

function Eval-GateScoreForSymbol([string]$sym, [string]$today) {
  $symU = $sym.Trim().ToUpperInvariant()
  $logs = Join-Path $repoRoot "logs"
  $gsDaily = Join-Path $logs ("gatescore_daily_summary_{0}.csv" -f $symU.ToLowerInvariant())
  if (-not (Test-Path $gsDaily)) { return @{ fresh=$false; samples_ok=$false; th_ok=$false; ok=$false } }

  $rows = @(Try-LoadCsv $gsDaily)

  # must have a REAL row for today
  $row = $null
  foreach ($r in $rows) {
    if ($null -eq $r) { continue }
    $d = "$($r.as_of_date)"
    if ($d.Length -ge 10) { $d = $d.Substring(0,10) }
    if ($d -ne $today) { continue }
    if ("$($r.source)".Trim().ToUpperInvariant() -ne "REAL") { continue }
    if ("$($r.symbol)".Trim().ToUpperInvariant() -ne $symU) { continue }
    $row = $r
  }
  if ($null -eq $row) { return @{ fresh=$false; samples_ok=$false; th_ok=$false; ok=$false } }

  $fresh = $true

  # thresholds
  $min_signals = 10
  $min_pnl_samples = 20
  $min_edge_abs = 0.50
  $min_micro_score = -0.05

  try {
    $cfg = Get-GateScoreThresholds $symU
    if ($null -ne $cfg) {
      if ($cfg.ContainsKey("min_signals")) { try { $min_signals = [int]$cfg.min_signals } catch {} }
      if ($cfg.ContainsKey("min_pnl_samples")) { try { $min_pnl_samples = [int]$cfg.min_pnl_samples } catch {} }
      if ($cfg.ContainsKey("min_edge_ratio")) { try { $min_edge_abs = [double]$cfg.min_edge_ratio } catch {} }
      if ($cfg.ContainsKey("min_micro_score")) { try { $min_micro_score = [double]$cfg.min_micro_score } catch {} }
    }
  } catch {}

  $count_signals = 0
  $pnl_samples = 0
  $edge_ratio = 0.0
  $micro = 0.0
  try {
    $count_signals = [int]("$($row.count_signals)")
    $pnl_samples = [int]("$($row.pnl_samples)")
    $edge_ratio = [double]("$($row.mean_edge_ratio)")
    $micro = [double]("$($row.mean_micro_score)")
  } catch {
    return @{ fresh=$fresh; samples_ok=$false; th_ok=$false; ok=$false }
  }

  $samples_ok = ($count_signals -ge $min_signals -and $pnl_samples -ge $min_pnl_samples)
  $th_ok = ([Math]::Abs($edge_ratio) -ge $min_edge_abs -and $micro -ge $min_micro_score)
  $ok = ($fresh -and $samples_ok -and $th_ok)

  return @{ fresh=$fresh; samples_ok=$samples_ok; th_ok=$th_ok; ok=$ok }
}

$today = Get-TodayStr
$logs  = Join-Path $repoRoot "logs"

$phase4 = Read-JsonSafe (Join-Path $logs "phase4_validation_passed.json")
$phase4_ok = $false
if ($null -ne $phase4) {
  $as = "$($phase4.as_of_date)"
  if ($as.Length -ge 10) { $as = $as.Substring(0,10) }
  $okv = $false
  try { $okv = [bool]$phase4.phase4_ok_today } catch { $okv = $false }
  if ($as -eq $today -and $okv) { $phase4_ok = $true }
}

$phase23_ok = Has-TodayRow (Try-LoadCsv (Join-Path $logs "phase23_health_daily.csv")) "date" $today
$evhard_ok  = Has-TodayRow (Try-LoadCsv (Join-Path $logs "phase5_ev_hard_veto_daily.csv")) "date" $today

$gs_nvda = Eval-GateScoreForSymbol "NVDA" $today
$gs_spy  = Eval-GateScoreForSymbol "SPY"  $today
$gs_qqq  = Eval-GateScoreForSymbol "QQQ"  $today

$obj = [ordered]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date = $today

  phase4_ok_today = [bool]$phase4_ok
  phase23_health_ok_today = [bool]$phase23_ok
  ev_hard_daily_ok_today = [bool]$evhard_ok

  # Symbol GateScore results (kept explicit for auditability)
  nvda_gatescore_ok_today = [bool]$gs_nvda.ok
  spy_gatescore_ok_today  = [bool]$gs_spy.ok
  qqq_gatescore_ok_today  = [bool]$gs_qqq.ok

  # Roll-up (legacy fields kept)
  gatescore_ok_today = [bool]($gs_nvda.ok -and $gs_spy.ok -and $gs_qqq.ok)

  nvda_blockg_ready = [bool]($phase4_ok -and $phase23_ok -and $evhard_ok -and $gs_nvda.ok)
  spy_blockg_ready  = [bool]($phase4_ok -and $phase23_ok -and $evhard_ok -and $gs_spy.ok)
  qqq_blockg_ready  = [bool]($phase4_ok -and $phase23_ok -and $evhard_ok -and $gs_qqq.ok)
}

$outJson = Join-Path $logs "blockg_status_stub.json"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outJson, ($obj | ConvertTo-Json -Depth 6), $utf8NoBom)

Write-Host "[BLOCK-G] Wrote $outJson" -ForegroundColor Green
Write-Host ("[BLOCK-G] today={0} phase4={1} phase23={2} evhard={3} nvda_ok={4} spy_ok={5} qqq_ok={6}" -f `
  $today,$phase4_ok,$phase23_ok,$evhard_ok,$obj.nvda_blockg_ready,$obj.spy_blockg_ready,$obj.qqq_blockg_ready) -ForegroundColor Cyan
exit 0