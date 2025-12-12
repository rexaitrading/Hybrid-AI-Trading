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
    if (("$v").Substring(0, [Math]::Min(10, ("$v").Length)) -eq $Today) { return $true }
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
  $outJson     = Join-Path $logs "blockg_status_stub.json"

  $phase23Rows = Try-LoadCsv -Path $phase23Path
  $evHardRows  = Try-LoadCsv -Path $evHardPath
  $gsRows      = Try-LoadCsv -Path $gsDailyPath

  # Conservative: require today rows to exist
  $phase23_ok = Has-TodayRow -Rows $phase23Rows -DateField "date" -Today $today
  $evhard_ok  = Has-TodayRow -Rows $evHardRows  -DateField "date" -Today $today
  $gs_ok      = Has-TodayRow -Rows $gsRows      -DateField "as_of_date" -Today $today

  $nvda_ready = ($phase23_ok -and $evhard_ok -and $gs_ok)

  $obj = [ordered]@{
    ts_utc                = (Get-Date).ToUniversalTime().ToString("o")
    as_of_date            = $today
    phase23_health_ok_today = [bool]$phase23_ok
    ev_hard_daily_ok_today  = [bool]$evhard_ok
    gatescore_fresh_today   = [bool]$gs_ok
    nvda_blockg_ready       = [bool]$nvda_ready
    spy_blockg_ready        = $false
    qqq_blockg_ready        = $false
  }

  ($obj | ConvertTo-Json -Depth 6) | Out-File -FilePath $outJson -Encoding utf8
  Write-Host "[BLOCK-G] Wrote $outJson" -ForegroundColor Green
  Write-Host ("[BLOCK-G] today={0} phase23_ok={1} evhard_ok={2} gatescore_ok={3} nvda_ready={4}" -f $today,$phase23_ok,$evhard_ok,$gs_ok,$nvda_ready)
}

Main