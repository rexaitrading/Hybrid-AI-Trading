[CmdletBinding()]
param(
  [string]$OutPath = ".\logs\ev_hard_evidence_raw.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Utf8NoBom([string]$Path, [string]$Text) {
  $enc = New-Object System.Text.UTF8Encoding($false)
  $full = $Path
  if (-not [System.IO.Path]::IsPathRooted($full)) {
    $repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
    $full = Join-Path $repoRoot $Path
  }
  $dir = Split-Path -Parent $full
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  [System.IO.File]::WriteAllText($full, $Text, $enc)
}
# Phase4 source (A2 preferred): prefer per-market phase4_status.json, then global phase4_status.json, else legacy stamp
# Phase4 evidence chooser (market-aware, fail-closed):
# Prefer per-market phase4_validation_passed.json, then per-market phase4_status.json,
# then global equivalents, then legacy phase4_stamp_last.json.
$phase4Path = ".\logs\phase4_validation_passed.json"
try {
  $mP4 = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant()
  if($mP4){
    $cand = ".\logs\" + $mP4 + "\phase4_validation_passed.json"
    if(Test-Path -LiteralPath $cand){ $phase4Path = $cand }
    else {
      $cand2 = ".\logs\" + $mP4 + "\phase4_status.json"
      if(Test-Path -LiteralPath $cand2){ $phase4Path = $cand2 }
    }
  }
  if(Test-Path -LiteralPath ".\logs\phase4_validation_passed.json"){ $phase4Path = ".\logs\phase4_validation_passed.json" }
  elseif(Test-Path -LiteralPath ".\logs\phase4_status.json"){ $phase4Path = ".\logs\phase4_status.json" }
  else {
    $alt = ".\logs\phase4_stamp_last.json"
    if(Test-Path -LiteralPath $alt){ $phase4Path = $alt }
  }
} catch { }
try {
  $m2 = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant()
  if($m2){
    $p = ".\logs\" + $m2 + "\phase4_status.json"
    if(Test-Path -LiteralPath $p){ $phase4Path = $p }
  }
  $p2 = ".\logs\phase4_status.json"
  if(Test-Path -LiteralPath $p2){ $phase4Path = $p2 }
} catch {}
# A2: fallback to Phase4 stamp if canonical file not present
if(-not (Test-Path -LiteralPath $phase4Path)){
  $alt = ".\logs\phase4_stamp_last.json"
  if(Test-Path -LiteralPath $alt){ $phase4Path = $alt }
}
# Market-aware TODAY (fail-closed): prefer Resolve-RunContext.as_of_date when HAT_MARKET set
# Market-aware TODAY (fail-closed): prefer Resolve-RunContext.as_of_date when HAT_MARKET set
$today = (Get-Date).ToString("yyyy-MM-dd")
try {
  $m = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant()
  $sym = (($env:HAT_SYMBOL + "")).Trim().ToUpperInvariant()
  if($m){
    if(-not $sym){ $sym = "NVDA" }
    $rcPath = Join-Path $PSScriptRoot "Resolve-RunContext.ps1"
    if(-not (Test-Path -LiteralPath $rcPath)){ throw "[FAIL-CLOSED] Missing Resolve-RunContext.ps1: $rcPath" }
    $rcRaw = (& $rcPath -Market $m -Symbol $sym | Out-String)
    $rcRaw = (($rcRaw + "")).Trim()
    if(-not $rcRaw){ throw "[FAIL-CLOSED] Resolve-RunContext empty stdout" }
    $ix0 = $rcRaw.IndexOf("{"); $ix1 = $rcRaw.LastIndexOf("}")
    if($ix0 -lt 0 -or $ix1 -le $ix0){ throw "[FAIL-CLOSED] Resolve-RunContext did not return JSON" }
    $rc = ($rcRaw.Substring($ix0, ($ix1 - $ix0 + 1))) | ConvertFrom-Json
    if(-not $rc -or -not $rc.as_of_date){ throw "[FAIL-CLOSED] Resolve-RunContext missing as_of_date" }
    $today = ([string]$rc.as_of_date).Trim()
    if($today.Length -ge 10){ $today = $today.Substring(0,10) }
  }
} catch {
  # fail-closed posture: keep $today as local date ONLY if RunContext cannot be resolved
}
try {
  $m = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant()
  $sym = (($env:HAT_SYMBOL + "")).Trim().ToUpperInvariant()
  if($m){
    if(-not $sym){ $sym = "NVDA" }
    $rcPath = Join-Path $PSScriptRoot "Resolve-RunContext.ps1"
    if(-not (Test-Path -LiteralPath $rcPath)){ throw "[FAIL-CLOSED] Missing Resolve-RunContext.ps1: $rcPath" }
    $rcRaw = (& $rcPath -Market $m -Symbol $sym | Out-String)
    $rcRaw = (($rcRaw + "")).Trim()
    if(-not $rcRaw){ throw "[FAIL-CLOSED] Resolve-RunContext empty stdout" }
    $ix0 = $rcRaw.IndexOf("{"); $ix1 = $rcRaw.LastIndexOf("}")
    if($ix0 -lt 0 -or $ix1 -le $ix0){ throw "[FAIL-CLOSED] Resolve-RunContext did not return JSON" }
    $rc = ($rcRaw.Substring($ix0, ($ix1 - $ix0 + 1))) | ConvertFrom-Json
    if(-not $rc -or -not $rc.as_of_date){ throw "[FAIL-CLOSED] Resolve-RunContext missing as_of_date" }
    $today = ([string]$rc.as_of_date).Trim()
    if($today.Length -ge 10){ $today = $today.Substring(0,10) }
  }
} catch {
  # fail-closed posture: keep $today as local date ONLY if RunContext cannot be resolved
}
# EVH_RAW_CANONICAL_ASOF_GUARD
$m_guard = (($env:HAT_MARKET + "")).Trim()
if(-not $m_guard){
# Canonical as-of: follow Phase4 stamp if present (prevents midnight boundary mismatch)
if(Test-Path $phase4Path){
  try {
    $j0 = (Get-Content $phase4Path -Raw) | ConvertFrom-Json
    $d0 = (($j0.as_of_date) + "").Trim()
    if($d0){ $today = $d0 }
  } catch {}
}
}
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")

# EVH_RAW_EFFECTIVE_TRADING_DAY_BEGIN
$effectiveTradingDay = $today
try {
  $effectiveTradingDay = (powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\Get-EffectiveTradingDay.ps1" -TodayOverride $today).Trim()
  if(-not $effectiveTradingDay){ $effectiveTradingDay = $today }
} catch { $effectiveTradingDay = $today }
# EVH_RAW_EFFECTIVE_TRADING_DAY_END

# EVH_RAW_INPUT_DAY_BEGIN
# On market-closed days, Phase4/Phase23 stamps may be "today" while effective trading day is Fri.
# Evaluate input freshness against snapshot_date (today) to avoid false-stale noise.
$inputsDay = $effectiveTradingDay
if ($effectiveTradingDay -ne $today) { $inputsDay = $today }
# EVH_RAW_INPUT_DAY_END



# ---- Phase4 ----
$phase4Ok = $false
$phase4AsOf = ""
if (Test-Path $phase4Path) {
  try {
    $j = (Get-Content $phase4Path -Raw) | ConvertFrom-Json
    $phase4AsOf = (($j.as_of_date) + "").Trim()
    try {
      if ($j.PSObject.Properties.Name -contains "ok") { $phase4Ok = [bool]$j.ok }
      elseif ($j.PSObject.Properties.Name -contains "phase4_ok_today") { $phase4Ok = [bool]$j.phase4_ok_today }
      else { $phase4Ok = $false }
    } catch { $phase4Ok = $false }
  } catch {}
}

# ---- Phase23 ----
$phase23Path = ".\logs\phase23_health_daily.csv"
$phase23Ok = $false
$phase23AsOf = ""
if (Test-Path $phase23Path) {
  try {
    $rows = @(Import-Csv $phase23Path)
    if ($rows.Count -gt 0) {
      $last = $rows | Sort-Object date | Select-Object -Last 1
      $phase23AsOf = (($last.date) + "").Trim()
      try {
  if($last.PSObject.Properties.Name -contains "ok"){ $phase23Ok = [bool]$last.ok }
  elseif($last.PSObject.Properties.Name -contains "phase23_ok"){ $phase23Ok = [bool]$last.phase23_ok }
  elseif($last.PSObject.Properties.Name -contains "phase23_ok_today"){ $phase23Ok = [bool]$last.phase23_ok_today }
  else { $phase23Ok = $false }
} catch { $phase23Ok = $false }
    }
  } catch {}
}

# ---- GateScore ----
$gsPath = ".\logs\gatescore_daily_summary.csv"
$gsOk = $false
$gsAsOf = ""
$gsFoundTodayRow = $false
$gsCountSignals = 0
if (Test-Path $gsPath) {
  try {
    $rows = @(Import-Csv $gsPath)
    $row = $rows | Where-Object { $_.symbol -eq "NVDA" -and ($_.as_of_date + "") -eq $inputsDay } | Select-Object -First 1
    if ($null -ne $row) {
      $gsFoundTodayRow = $true
      $gsAsOf = (($row.as_of_date) + "").Trim()
      # evidence-only: count_signals>0; strict thresholds enforced downstream (Block-G)
      [void][int]::TryParse([string]$row.count_signals, [ref]$gsCountSignals)
      $gsOk = ($gsCountSignals -gt 0)
    }
  } catch {}
}

# ---- Decision (fail-closed) ----
$ok = $false
$reason = "missing_inputs_failclosed"
$reasons = New-Object System.Collections.Generic.List[string]
$warnings = New-Object System.Collections.Generic.List[string]

if ($phase4AsOf -ne $inputsDay -or -not $phase4Ok) { $reasons.Add("phase4_not_ok_or_stale") }
if ($phase23AsOf -ne $inputsDay -or -not $phase23Ok) { $reasons.Add("phase23_not_ok_or_stale") }
# GateScore is recorded as a warning here; Block-G enforces strict today-ness for LIVE readiness
if ($gsAsOf -ne $inputsDay -or -not $gsOk) { $warnings.Add("gatescore_not_ok_or_missing_today_row") }

if ($reasons.Count -eq 0) {
  $ok = $true
  $reason = "raw_inputs_all_green"
} else {
  $ok = $false
  $reason = ($reasons -join ";")
}

$out = [ordered]@{
  ts_utc = $tsUtc
  as_of_date = $inputsDay
  snapshot_date = $today
  effective_trading_day = $effectiveTradingDay
  ok = $ok
  ok_today = $ok
  reason = $reason
  warnings = @($warnings)
  inputs = [ordered]@{
    phase4 = [ordered]@{ as_of_date=$phase4AsOf; ok=$phase4Ok; path=$phase4Path }
    phase23 = [ordered]@{ as_of_date=$phase23AsOf; ok=$phase23Ok; path=$phase23Path }
    gatescore = [ordered]@{
      as_of_date = $gsAsOf
      ok = $gsOk
      found_today_row = $gsFoundTodayRow
      count_signals = $gsCountSignals
      path = $gsPath
      symbol = "NVDA"
    }
  }
} | ConvertTo-Json -Depth 8

Write-Utf8NoBom -Path $OutPath -Text ($out + "`n")
Write-Host ("[EV-HARD-RAW] wrote {0} ok={1} reason={2}" -f $OutPath,$ok,$reason) -ForegroundColor Cyan
exit 0
