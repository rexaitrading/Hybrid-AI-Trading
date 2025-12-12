Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-TodayStr { (Get-Date).ToString("yyyy-MM-dd") }

function Try-LoadCsv {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (-not (Test-Path $Path)) { return @() }
  try { return @(Import-Csv $Path) } catch { return @() }
}

function Has-TodayRow {
  param(
    [Parameter(Mandatory=$true)]$Rows,
    [Parameter(Mandatory=$true)][string]$DateField,
    [Parameter(Mandatory=$true)][string]$Today
  )
  foreach ($r in $Rows) {
    if ($null -eq $r) { continue }
    $v = $r.$DateField
    if ($null -eq $v) { continue }
    $s = "$v"
    if ($s.Length -ge 10) { $s = $s.Substring(0,10) }
    if ($s -eq $Today) { return $true }
  }
  return $false
}

function Main {
  $repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
  $logs = Join-Path $repoRoot "logs"
  $today = Get-TodayStr

  $phase23Path = Join-Path $logs "phase23_health_daily.csv"
  $evHardPath  = Join-Path $logs "phase5_ev_hard_veto_daily.csv"
  $gsDailyPath = Join-Path $logs "gatescore_daily_summary.csv"
  $phase4Stamp = Join-Path $logs "phase4_validation_passed.json"
  $outJson     = Join-Path $logs "blockg_status_stub.json"

  $phase23Rows = Try-LoadCsv -Path $phase23Path
  $evHardRows  = Try-LoadCsv -Path $evHardPath
  $gsRows      = Try-LoadCsv -Path $gsDailyPath

  # Conservative: require today rows to exist
  $phase23_ok = Has-TodayRow -Rows $phase23Rows -DateField "date" -Today $today
  $evhard_ok  = Has-TodayRow -Rows $evHardRows  -DateField "date" -Today $today

  # Phase-4 stamp (must be present and today)
  $phase4_ok = $false
  if (Test-Path $phase4Stamp) {
    try {
      $j = Get-Content $phase4Stamp -Raw | ConvertFrom-Json
      if ($null -ne $j -and "$($j.as_of_date)" -eq $today -and [bool]$j.phase4_ok_today) {
        $phase4_ok = $true
      }
    } catch { $phase4_ok = $false }
  }

  # GateScore checks (fresh + samples + threshold)
  $gs_fresh = Has-TodayRow -Rows $gsRows -DateField "as_of_date" -Today $today

  $min_signals = 5
  $min_pnl_samples = 4
  $min_edge_ratio = 0.01    # conservative: must be meaningfully positive
  $min_micro_score = -0.05  # avoid severely negative micro quality

  $gs_samples_ok = $false
  $gs_threshold_ok = $false

  if ($gs_fresh) {
    # Find today's NVDA row if present
    $row = $null
    foreach ($r in $gsRows) {
      if ($null -eq $r) { continue }
      if ("$($r.as_of_date)".Substring(0,10) -ne $today) { continue }
      if ($r.PSObject.Properties.Name -contains "symbol") {
        if ("$($r.symbol)" -ne "NVDA") { continue }
      }
      $row = $r
      break
    }

    if ($null -ne $row) {
      try {
        $count_signals = [int]("$($row.count_signals)")
        $pnl_samples   = [int]("$($row.pnl_samples)")
        $edge_ratio    = [double]("$($row.mean_edge_ratio)")
        $micro_score   = [double]("$($row.mean_micro_score)")

        $gs_samples_ok   = ($count_signals -ge $min_signals -and $pnl_samples -ge $min_pnl_samples)
        $gs_threshold_ok = ($edge_ratio -ge $min_edge_ratio -and $micro_score -ge $min_micro_score)
      } catch {
        $gs_samples_ok = $false
        $gs_threshold_ok = $false
      }
    }
  }

  $gs_ok = ($gs_fresh -and $gs_samples_ok -and $gs_threshold_ok)

  $nvda_ready = ($phase4_ok -and $phase23_ok -and $evhard_ok -and $gs_ok)

  $obj = [ordered]@{
    ts_utc                     = (Get-Date).ToUniversalTime().ToString("o")
    as_of_date                 = $today

    phase4_ok_today            = [bool]$phase4_ok
    phase23_health_ok_today    = [bool]$phase23_ok
    ev_hard_daily_ok_today     = [bool]$evhard_ok

    gatescore_fresh_today      = [bool]$gs_fresh
    gatescore_samples_ok_today = [bool]$gs_samples_ok
    gatescore_threshold_ok_today = [bool]$gs_threshold_ok
    gatescore_ok_today         = [bool]$gs_ok

    nvda_blockg_ready          = [bool]$nvda_ready
    spy_blockg_ready           = $false
    qqq_blockg_ready           = $false
  }

  ($obj | ConvertTo-Json -Depth 6) | Out-File -FilePath $outJson -Encoding utf8
  Write-Host "[BLOCK-G] Wrote $outJson" -ForegroundColor Green
  Write-Host ("[BLOCK-G] today={0} phase4_ok={1} phase23_ok={2} evhard_ok={3} gs_ok={4} nvda_ready={5}" -f $today,$phase4_ok,$phase23_ok,$evhard_ok,$gs_ok,$nvda_ready)
}

Main