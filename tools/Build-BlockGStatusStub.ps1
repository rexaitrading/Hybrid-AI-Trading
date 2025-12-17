param(
  [Parameter(Mandatory=$false)][ValidateSet("NVDA","SPY","QQQ")][string]$Symbol = "NVDA"
)

function As-Array {
  param([Parameter(ValueFromPipeline=$true)]$InputObject)
  if ($null -eq $InputObject) { return @() }
  if ($InputObject -is [System.Array]) { return $InputObject }
  return @($InputObject)
}

function Get-GateScoreThresholds {
  param([string]$Symbol)
  $p = "docs\thresholds\gatescore_thresholds.psd1"
  if (-not (Test-Path $p)) { return $null }
  $th = Import-PowerShellDataFile -Path $p
  $cfg = $th[$Symbol]
  if (-not $cfg) { $cfg = $th["DEFAULT"] }
  return $cfg
}

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
    [Parameter()]$Rows,
    [Parameter(Mandatory=$true)][string]$DateField,
    [Parameter(Mandatory=$true)][string]$Today
  )

# Normalize symbol param (StrictMode-safe)
if (Get-Variable -Name Symbol -ErrorAction SilentlyContinue) {
  # ok: already $Symbol
} elseif (Get-Variable -Name symbol -ErrorAction SilentlyContinue) {
  $Symbol = $symbol
} else {
  throw "[BLOCK-G] Missing -Symbol parameter (no $Symbol/$symbol variable found)."
}
if ([string]::IsNullOrWhiteSpace("$Symbol")) { throw "[BLOCK-G] -Symbol is empty." }
$Symbol = ("$Symbol").Trim().ToUpperInvariant()

  if (-not $Rows) { return $false }
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
  param([Parameter(Mandatory=$true)][string]$Symbol)
  $repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
  $logs = Join-Path $repoRoot "logs"
  $today = Get-TodayStr

  # Normalize Symbol (StrictMode-safe)
  $Symbol = ("$Symbol").Trim().ToUpperInvariant()
  if ([string]::IsNullOrWhiteSpace($Symbol)) { throw "[BLOCK-G] -Symbol is empty." }


  $phase23Path = Join-Path $logs "phase23_health_daily.csv"
  $evHardPath  = Join-Path $logs "phase5_ev_hard_veto_daily.csv"
  $gsDailyPath = Join-Path $logs ("gatescore_daily_summary_{0}.csv" -f $Symbol.ToLowerInvariant())
  if (-not (Test-Path $gsDailyPath)) {
    $gsDailyPath = Join-Path $logs "gatescore_daily_summary.csv"  # fallback
  }
  $phase4Stamp = Join-Path $logs "phase4_validation_passed.json"
  $outJson     = Join-Path $logs ("blockg_status_stub_{0}.json" -f $Symbol.ToLowerInvariant())

  # Diagnostics: show missing inputs (log-only)
  if (-not (Test-Path $phase23Path)) { Write-Host "[BLOCK-G] MISSING $phase23Path" -ForegroundColor Yellow }
  if (-not (Test-Path $evHardPath))  { Write-Host "[BLOCK-G] MISSING $evHardPath" -ForegroundColor Yellow }
  if (-not (Test-Path $gsDailyPath)) { Write-Host "[BLOCK-G] MISSING $gsDailyPath" -ForegroundColor Yellow }
  if (-not (Test-Path $phase4Stamp)) { Write-Host "[BLOCK-G] MISSING $phase4Stamp" -ForegroundColor Yellow }

  $phase23Rows = (@(Try-LoadCsv -Path $phase23Path))
  $evHardRows  = (@(Try-LoadCsv -Path $evHardPath))
$gsRows      = @(Try-LoadCsv -Path $gsDailyPath)
  # Conservative: require today rows to exist
  $phase23_ok = Has-TodayRow -Rows $phase23Rows -DateField "date" -Today $today
  $evhard_ok  = Has-TodayRow -Rows $evHardRows  -DateField "date" -Today $today
# Phase-4 stamp (must be present and today) (BOM-safe, fail-closed)
  $phase4_ok = $false
  if (Test-Path $phase4Stamp) {
    try {
      $raw = Get-Content $phase4Stamp -Raw -Encoding utf8
      if ($raw.Length -gt 0 -and [int][char]$raw[0] -eq 65279) { $raw = $raw.TrimStart([char]65279) }
      $j = $raw | ConvertFrom-Json -ErrorAction Stop
      $as = "$($j.as_of_date)"
      if ($as.Length -ge 10) { $as = $as.Substring(0,10) }
      $okv = $false
      try { $okv = [bool]$j.phase4_ok_today } catch { $okv = $false }
      if ($as -eq $today -and $okv) { $phase4_ok = $true }
      if (-not $phase4_ok) {
        Write-Host ("[BLOCK-G] PHASE4_STAMP parsed but not OK: as_of_date={0} today={1} phase4_ok_today={2}" -f $as,$today,$okv) -ForegroundColor Yellow
      }
    } catch {
      Write-Host ("[BLOCK-G] PHASE4_STAMP parse failed: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
      $phase4_ok = $false
    }
  }

  # GateScore checks (fresh + samples + threshold)
    # GateScore freshness is REAL-only (prevents stub arming)
  $gs_fresh = $false
  if ($gsRows -and ($gsRows[0].PSObject.Properties.Name -contains "as_of_date") -and ($gsRows[0].PSObject.Properties.Name -contains "source")) {
    foreach ($r in $gsRows) {
      if ($null -eq $r) { continue }
      $d = "$($r.as_of_date)"
      if ($d.Length -ge 10) { $d = $d.Substring(0,10) }
      if ($d -ne $today) { continue }
      if ("$($r.source)".Trim().ToUpperInvariant() -ne "REAL") { continue }
      # If symbol column exists, require NVDA for NVDA gating
      if ($r.PSObject.Properties.Name -contains "source") { if ("$($r.source)".Trim().ToUpperInvariant() -ne "REAL") { continue } }
      if ($r.PSObject.Properties.Name -contains "symbol") {
        if ("$($r.symbol)".Trim().ToUpperInvariant() -ne $Symbol) { continue }
      }
      $gs_fresh = $true
      break
    }
  }
# Thresholds (symbol-specific) fail-closed defaults
  $min_signals = 10
  $min_pnl_samples = 20
  $min_edge_abs = 0.50
  $min_micro_score = -0.05

  try {
    $cfg = Get-GateScoreThresholds $Symbol
    if ($null -ne $cfg) {
      if ($cfg.ContainsKey("min_signals")) { try { $min_signals = [int]$cfg.min_signals } catch { } }
      if ($cfg.ContainsKey("min_pnl_samples")) { try { $min_pnl_samples = [int]$cfg.min_pnl_samples } catch { } }
      # psd1 uses min_edge_ratio; Block-G uses abs(edge) threshold
      if ($cfg.ContainsKey("min_edge_ratio")) { try { $min_edge_abs = [double]$cfg.min_edge_ratio } catch { } }
      if ($cfg.ContainsKey("min_micro_score")) { try { $min_micro_score = [double]$cfg.min_micro_score } catch { } }
    }
  } catch { }

  $gs_samples_ok = $false
  $gs_threshold_ok = $false

  if ($gs_fresh) {
    # Find today's NVDA row if present
    $row = $null
    foreach ($r in $gsRows) {
      if ($null -eq $r) { continue }
      if ("$($r.as_of_date)".Substring(0,10) -ne $today) { continue }
      if ($r.PSObject.Properties.Name -contains "source") { if ("$($r.source)".Trim().ToUpperInvariant() -ne "REAL") { continue } }
      if ($r.PSObject.Properties.Name -contains "symbol") {
        if ("$($r.symbol)".Trim().ToUpperInvariant() -ne $Symbol) { continue }
      }
      $row = $r
      # keep scanning; take LAST match
    }

    if ($null -ne $row) {
      try {
        $count_signals = [int]("$($row.count_signals)")
        $pnl_samples   = [int]("$($row.pnl_samples)")
        $edge_ratio    = [double]("$($row.mean_edge_ratio)")
        $micro_score   = [double]("$($row.mean_micro_score)")


        Write-Host ("[BLOCK-G] GS_PICKED date={0} sym={1} src={2} signals={3} pnl={4} edge={5} micro={6}" -f `
          $today, "$($row.symbol)", "$($row.source)", $count_signals, $pnl_samples, $edge_ratio, $micro_score) -ForegroundColor Cyan
        $gs_samples_ok   = ($count_signals -ge $min_signals -and $pnl_samples -ge $min_pnl_samples)
        $edge_abs = [Math]::Abs($edge_ratio)
        $gs_threshold_ok = ($edge_abs -ge $min_edge_abs -and $micro_score -ge $min_micro_score)
      } catch {
        $gs_samples_ok = $false
        $gs_threshold_ok = $false
      }
    }
  }

  $gs_ok = ($gs_fresh -and $gs_samples_ok -and $gs_threshold_ok)

  $nvda_ready = ($phase4_ok -and $phase23_ok -and $evhard_ok -and $gs_ok)

  $obj = [ordered]@{
    ts_utc                       = (Get-Date).ToUniversalTime().ToString("o")
    as_of_date                   = $today

    phase4_ok_today              = [bool]$phase4_ok
    phase23_health_ok_today      = [bool]$phase23_ok
    ev_hard_daily_ok_today       = [bool]$evhard_ok

    gatescore_fresh_today        = [bool]$gs_fresh
    gatescore_samples_ok_today   = [bool]$gs_samples_ok
    gatescore_threshold_ok_today = [bool]$gs_threshold_ok
    gatescore_ok_today           = [bool]$gs_ok

    nvda_blockg_ready            = [bool]($phase4_ok -and $phase23_ok -and $evhard_ok -and $gs_ok -and ($Symbol -eq "NVDA"))
    spy_blockg_ready             = [bool]($phase4_ok -and $phase23_ok -and $evhard_ok -and $gs_ok -and ($Symbol -eq "SPY"))
    qqq_blockg_ready             = [bool]($phase4_ok -and $phase23_ok -and $evhard_ok -and $gs_ok -and ($Symbol -eq "QQQ"))
  }

  $json = ($obj | ConvertTo-Json -Depth 6)
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($outJson, $json, $utf8NoBom)
  Write-Host "[BLOCK-G] Wrote $outJson" -ForegroundColor Green
  # Compat: keep legacy single-file path updated for NVDA only (do not clobber other symbols)
  if ($Symbol -eq "NVDA") {
    $legacyPath = Join-Path $logs "blockg_status_stub.json"
    try { Copy-Item -Force $outJson $legacyPath } catch { }
  }
  Write-Host ("[BLOCK-G] today={0} phase4_ok={1} phase23_ok={2} evhard_ok={3} gs_ok={4} nvda_ready={5}" -f $today,$phase4_ok,$phase23_ok,$evhard_ok,$gs_ok,($obj.nvda_blockg_ready))
}
Main -Symbol $Symbol
