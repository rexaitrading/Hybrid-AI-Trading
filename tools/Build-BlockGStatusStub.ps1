[CmdletBinding()]
param(
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---- paths ----
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsDir  = Join-Path $repoRoot "logs"
if(-not (Test-Path -LiteralPath $logsDir)){ New-Item -ItemType Directory -Path $logsDir | Out-Null }
$statusPath = Join-Path $logsDir "blockg_status_stub.json"

Write-Output ("blockg_status_stub.json -> " + $statusPath)

function To-Bool($v){
  if($v -is [bool]){ return $v }
  $s = ("" + $v).Trim().ToLower()
  return ($s -eq "true")
}

function Read-JsonSafe([string]$path){
  try {
    if(Test-Path -LiteralPath $path){
      return (Get-Content -LiteralPath $path -Raw -Encoding utf8 | ConvertFrom-Json)
    }
  } catch {}
  return $null
}

function Effective-AsofDate([string]$logsDir){
  $today = (Get-Date).ToString("yyyy-MM-dd")
  $dow = (Get-Date).DayOfWeek
  $isWeekend = ($dow -eq "Saturday" -or $dow -eq "Sunday")
  if(-not $isWeekend){ return $today }

  $cands = New-Object System.Collections.Generic.List[string]
  try {
    $gs = Join-Path $logsDir "gatescore_daily_summary.csv"
    if(Test-Path -LiteralPath $gs){
      $d = (Import-Csv $gs | ForEach-Object { $_.as_of_date } | Where-Object { $_ } | Sort-Object | Select-Object -Last 1)
      if($d){ [void]$cands.Add(($d+"").Trim()) }
    }
  } catch {}
  try {
    $p4 = Join-Path $logsDir "phase4_validation_passed.json"
    $j = Read-JsonSafe $p4
    if($null -ne $j){
      $d = (($j.as_of_date + "").Trim())
      if($d){ [void]$cands.Add($d) }
    }
  } catch {}

  if($cands.Count -gt 0){ return ($cands | Sort-Object | Select-Object -Last 1) }
  return $today
}

function Get-Phase4OkToday([string]$logsDir, [string]$asOf){
  $p = Join-Path $logsDir "phase4_validation_passed.json"
  $j = Read-JsonSafe $p
  if($null -eq $j){ return $false }
  try {
    $d = ("" + $j.as_of_date).Substring(0,10)
    $ok = To-Bool $j.phase4_ok_today
    if($d -ne $asOf){ return $false }
    if(-not $ok){ return $false }
    return $true
  } catch { return $false }
}

function Get-EvHardOkToday([string]$logsDir, [string]$asOf){
  # Prefer canonical daily CSV if present; fallback to raw evidence JSON (legacy).
  $csv = Join-Path $logsDir "phase5_ev_hard_veto_daily.csv"
  if(Test-Path -LiteralPath $csv){
    try {
      $rows = @(Import-Csv -LiteralPath $csv)
      foreach($r in $rows){
        $d = ""
        if($r.PSObject.Properties.Name -contains "as_of_date"){ $d = ("" + $r.as_of_date).Trim() }
        elseif($r.PSObject.Properties.Name -contains "date"){ $d = ("" + $r.date).Trim() }
        if($d -eq $asOf){
          # ok column may be "True"/"False" string; normalize
          return (To-Bool $r.ok)
        }
      }
      # If CSV exists but no row for asOf => fail-closed
      return $false
    } catch {
      return $false
    }
  }

  # Fallback: ev_hard_evidence_raw.json
  $raw = Join-Path $logsDir "ev_hard_evidence_raw.json"
  if(-not (Test-Path -LiteralPath $raw)){ return $false }

  try {
    $j = Read-JsonSafe $raw
    if($null -eq $j){ return $false }

    # If file has a date field, require it matches asOf
    foreach($k in @("as_of_date","date","session_date","effective_as_of")){
      if($j.PSObject.Properties[$k]){
        $d = ("" + $j.$k).Trim()
        if($d -ne ""){
          if($d -ne $asOf){ return $false }
        }
      }
    }

    # Prefer explicit ok/pass fields
    foreach($k in @("ev_hard_daily_ok_today","ok","passed","pass","ev_hard_ok")){
      if($j.PSObject.Properties[$k]){
        return (To-Bool $j.$k)
      }
    }

    # Last resort: string heuristic for '"passed": true' or '"ok": true'
    $s = Get-Content -LiteralPath $raw -Raw -Encoding utf8
    if($s -match '"passed"\s*:\s*true' -or $s -match '"ok"\s*:\s*true'){ return $true }
    return $false
  } catch { return $false }
}

function Get-GateScoreSessionDate([string]$logsDir){
  $gs = Join-Path $logsDir "gatescore_daily_summary.csv"
  if(Test-Path -LiteralPath $gs){
    try {
      $rows = @(Import-Csv $gs)
      if($rows.Count -gt 0){
        $d = ("" + $rows[-1].as_of_date).Trim()
        if($d){ return $d }
      }
    } catch {}
  }
  return ""
}

# --- Official GateScore events evidence (fail-closed) ---
function Count-JsonlLines([string]$Path){
  try {
    if(-not (Test-Path -LiteralPath $Path)){ return 0 }
    $n = 0
    foreach($x in (Get-Content -LiteralPath $Path -Encoding utf8)){ if(($x+"").Trim()){ $n++ } }
    return [int]$n
  } catch { return 0 }
}


function EventsFileFor([string]$logsDir, [string]$sym){
  $u = ($sym + "").Trim().ToUpper()
  if($u -eq "NVDA"){
    $p = Join-Path $logsDir "nvda_gatescore_events.jsonl"
    if(Test-Path -LiteralPath $p){
      if((Get-Item -LiteralPath $p).Length -gt 0){ return $p }
    }
    $p2 = Join-Path $logsDir "nvda_gatescore_events_stub.jsonl"
    if(Test-Path -LiteralPath $p2){
      if((Get-Item -LiteralPath $p2).Length -gt 0){ return $p2 }
    }
    return $p
  }
  if($u -eq "SPY"){ return (Join-Path $logsDir "spy_gatescore_events.jsonl") }
  if($u -eq "QQQ"){ return (Join-Path $logsDir "qqq_gatescore_events.jsonl") }
  return ""
}

function Has-NonEmpty([string]$p){
  if(-not $p){ return $false }
  if(-not (Test-Path -LiteralPath $p)){ return $false }
  try { return ((Get-Item -LiteralPath $p).Length -gt 0) } catch { return $false }
}

# ---- GateScore quality helpers ----
function Get-GateScoreRow([string]$logsDir, [string]$sym, [string]$asOf){
  $p = Join-Path $logsDir "gatescore_daily_summary.csv"
  if(-not (Test-Path -LiteralPath $p)){ return $null }
  try {
    $rows = @(Import-Csv $p)
    $u = ($sym + "").Trim().ToUpper()
    $last = $null
    foreach($r in $rows){
      if((("" + $r.symbol).Trim().ToUpper() -eq $u) -and (("" + $r.as_of_date).Trim() -eq $asOf)){
        $last = $r
      }
    }
    return $last
  } catch { return $null }
}

function To-Num($v){ try { return [double]("" + $v) } catch { return [double]0 } }

function GateScoreOkFromRow($row){
  # thresholds (tune later via config)
  $MIN_SIGNALS = 30
  $MIN_PNL_SAMPLES = 30
  $MIN_MICRO_SCORE = 0.10
  $MIN_EDGE_RATIO  = 0.05

  if($null -eq $row){ return $false }
  $countSignals = To-Num $row.count_signals
  $pnlSamples   = To-Num $row.pnl_samples
  $microScore   = To-Num $row.mean_micro_score
  $edgeRatio    = To-Num $row.mean_edge_ratio

  if($countSignals -lt $MIN_SIGNALS){ return $false }
  if($pnlSamples -lt $MIN_PNL_SAMPLES){ return $false }
  if(($microScore -le 0) -and ($edgeRatio -le 0)){ return $false }
  if($microScore -lt $MIN_MICRO_SCORE){ return $false }
  if($edgeRatio -lt $MIN_EDGE_RATIO){ return $false }
  return $true
}

# ---- payload ----
$asOf = Effective-AsofDate $logsDir

# --- GateScore stamp load (preferred over CSV heuristics; fail-closed) ---
$stampPath = Join-Path $logsDir "gatescore_stamp.json"
$stamp = $null
if(Test-Path -LiteralPath $stampPath){ $stamp = Read-JsonSafe $stampPath }
# --- end stamp load ---

function Apply-GateScoreFromStamp([ref]$payload, $stamp){
  # Fail-closed defaults
  $payload.Value.gatescore_as_of_date = ""
  $payload.Value.gatescore_fresh_for_session = $false
  $payload.Value.gatescore_fresh_today = $false
  $payload.Value.gatescore_ok_today = $false

  $payload.Value.gatescore_rows_today = 0
  $payload.Value.gatescore_min_samples_ok_today = $false
  $payload.Value.gatescore_stable_today = $false
  $payload.Value.gatescore_stamp_reasons = @()

  if($null -eq $stamp){
    $payload.Value.gatescore_stamp_reasons = @("missing_gatescore_stamp")
    return
  }

  try {
    $sd = ""
    if($stamp.PSObject.Properties.Name -contains "as_of_date"){ $sd = ("" + $stamp.as_of_date).Trim() }
    $payload.Value.gatescore_as_of_date = $sd
    $payload.Value.gatescore_fresh_for_session = ($sd -ne "" -and $sd -eq $payload.Value.as_of_date)
    $payload.Value.gatescore_fresh_today = (To-Bool $payload.Value.gatescore_fresh_for_session)

    if($stamp.PSObject.Properties.Name -contains "gatescore_rows_today"){ $payload.Value.gatescore_rows_today = [int]("" + $stamp.gatescore_rows_today) }
    if($stamp.PSObject.Properties.Name -contains "gatescore_min_samples_ok_today"){ $payload.Value.gatescore_min_samples_ok_today = (To-Bool $stamp.gatescore_min_samples_ok_today) }
    if($stamp.PSObject.Properties.Name -contains "gatescore_stable_today"){ $payload.Value.gatescore_stable_today = (To-Bool $stamp.gatescore_stable_today) }
    if($stamp.PSObject.Properties.Name -contains "reasons"){ $payload.Value.gatescore_stamp_reasons = @($stamp.reasons) }

    # STRICT OK: must be fresh + rows>0 + min samples + stable
    $payload.Value.gatescore_ok_today = $false
    if((To-Bool $payload.Value.gatescore_fresh_today)){
      if(($payload.Value.gatescore_rows_today -gt 0)){
        if((To-Bool $payload.Value.gatescore_min_samples_ok_today)){
          if((To-Bool $payload.Value.gatescore_stable_today)){
            $payload.Value.gatescore_ok_today = $true
          }
        }
      }
    }
  } catch {
    # fail-closed
    $payload.Value.gatescore_ok_today = $false
    $payload.Value.gatescore_fresh_today = $false
    $payload.Value.gatescore_stamp_reasons = @("gatescore_stamp_parse_failed")
  }
}
$payload = [ordered]@{
  as_of_date = $asOf

  gatescore_as_of_date = ""
  gatescore_fresh_for_session = $false
  gatescore_fresh_today = $false
  gatescore_ok_today = $false

  # GateScore stamp (deterministic) - fail-closed
  gatescore_rows_today = 0
  gatescore_min_samples_ok_today = $false
  gatescore_stable_today = $false
  gatescore_stamp_reasons = @()

  phase4_ok_today = $false
  ev_hard_daily_ok_today = $false

  # Evidence-only: today-row validation for daily CSV artifacts (builder-owned; checker is contract-only)
  phase23_health_today_row_ok = $false
  phase23_health_last_date    = ""
  ev_hard_today_row_ok        = $false
  ev_hard_last_date           = ""

  nvda_blockg_ready = $false
  nvda_gatescore_events_count_today = 0
  nvda_gatescore_events_min_required = 10
  nvda_gatescore_events_ok_today = $false
  spy_blockg_ready  = $false
  qqq_blockg_ready  = $false

  reasons_not_ready = @()
}

# Phase4 + EV-hard
$payload.phase4_ok_today = (Get-Phase4OkToday $logsDir $asOf)
$payload.ev_hard_daily_ok_today = (Get-EvHardOkToday $logsDir $asOf)

# GateScore as_of + freshness

$gsAsOf = (Get-GateScoreSessionDate $logsDir)
$payload.gatescore_as_of_date = $gsAsOf
if($gsAsOf -ne ""){
  $payload.gatescore_fresh_for_session = ($gsAsOf -eq $asOf)
}

# Institutional invariant
if(($payload.gatescore_as_of_date + "") -eq ""){
  $payload.gatescore_fresh_for_session = $false
  $payload.gatescore_fresh_today = $false
} elseif(($payload.gatescore_as_of_date + "") -eq ($payload.as_of_date + "")){
  $payload.gatescore_fresh_today = (To-Bool $payload.gatescore_fresh_for_session)
} else {
  $payload.gatescore_fresh_today = $false
}

# --- Apply GateScore stamp STRICT (no fallback; fail-closed) ---
$payloadRef = [ref]$payload
Apply-GateScoreFromStamp -payload $payloadRef -stamp $stamp
# --- end GateScore stamp ---

# Tighten-only: "fresh" requires at least one GateScore row today (prevents misleading fresh+empty).
if([int]$payload.gatescore_rows_today -le 0){
  $payload.gatescore_fresh_for_session = $false
  $payload.gatescore_fresh_today = $false
  $payload.gatescore_ok_today = $false
}




# GateScore ok today (quality):
# (computed strictly from gatescore_stamp.json; no fallbacks)

# NVDA readiness (PS-safe; no -and operators)
$payload.nvda_blockg_ready = $false

# --- NVDA official GateScore events evidence (builder-owned; contract-only later) ---
$payload.nvda_gatescore_events_count_today = 0
$payload.nvda_gatescore_events_min_required = 10
$payload.nvda_gatescore_events_ok_today = $false
try {
  $ev = (EventsFileFor $logsDir "NVDA")
  if($ev -and (Test-Path -LiteralPath $ev)){
    $payload.nvda_gatescore_events_count_today = (Count-JsonlLines $ev)
    if([int]$payload.nvda_gatescore_events_count_today -ge [int]$payload.nvda_gatescore_events_min_required){
      $payload.nvda_gatescore_events_ok_today = $true
    }
  }
} catch {
  $payload.nvda_gatescore_events_ok_today = $false
}
# --- end events evidence ---


## --- C.5 today-row validation (builder-owned; contract carries evidence) ---
try {
  $p23 = Join-Path $logsDir "phase23_health_daily.csv"
  if(Test-Path -LiteralPath $p23){
    $r23 = @(Import-Csv -LiteralPath $p23)
    if($r23.Count -gt 0){
      $last = $r23[-1]
      $d23 = ""
      if($last.PSObject.Properties.Name -contains "as_of_date"){ $d23 = ("" + $last.as_of_date).Trim() }
      elseif($last.PSObject.Properties.Name -contains "date"){ $d23 = ("" + $last.date).Trim() }
      $payload.phase23_health_last_date = $d23
      if($d23 -eq $asOf){ $payload.phase23_health_today_row_ok = $true }
    }
  }
} catch { }
try {
  $pev = Join-Path $logsDir "phase5_ev_hard_veto_daily.csv"
  if(Test-Path -LiteralPath $pev){
    $rev = @(Import-Csv -LiteralPath $pev)
    if($rev.Count -gt 0){
      $rowLast = $rev[-1]
      $dlast = ""
      if($rowLast.PSObject.Properties.Name -contains "as_of_date"){ $dlast = ("" + $rowLast.as_of_date).Trim() }
      elseif($rowLast.PSObject.Properties.Name -contains "date"){ $dlast = ("" + $rowLast.date).Trim() }
      $payload.ev_hard_last_date = $dlast
    }
    $hit = @($rev | Where-Object {
      $d = ""
      if($_.PSObject.Properties.Name -contains "as_of_date"){ $d = ("" + $_.as_of_date).Trim() }
      elseif($_.PSObject.Properties.Name -contains "date"){ $d = ("" + $_.date).Trim() }
      $d -eq $asOf
    })
    if($hit.Count -gt 0){ $payload.ev_hard_today_row_ok = $true }
  }
} catch { }
## --- end today-row validation ---

if((To-Bool $payload.phase4_ok_today)){
  if((To-Bool $payload.ev_hard_daily_ok_today)){
    if((To-Bool $payload.gatescore_ok_today)){
      if((To-Bool $payload.gatescore_fresh_today)){
        if((To-Bool System.Collections.Specialized.OrderedDictionary.nvda_gatescore_events_ok_today)){
          $payload.nvda_blockg_ready = $true
        }
      }
    }
  }
}

# SPY readiness from daily_summary row
$payload.spy_blockg_ready = $false
if((To-Bool $payload.gatescore_fresh_today)){
  $spyRow = Get-GateScoreRow $logsDir "SPY" $asOf
  if(GateScoreOkFromRow $spyRow){ $payload.spy_blockg_ready = $true }
}

# QQQ readiness from daily_summary row
$payload.qqq_blockg_ready = $false
if((To-Bool $payload.gatescore_fresh_today)){
  $qqqRow = Get-GateScoreRow $logsDir "QQQ" $asOf
  if(GateScoreOkFromRow $qqqRow){ $payload.qqq_blockg_ready = $true }
}

# Reasons (canonical)
$rn = @()
if($payload.PSObject.Properties.Name -contains "gatescore_stamp_reasons"){
  foreach($r in @($payload.gatescore_stamp_reasons)){
    $s = ("" + $r).Trim()
    if($s){ $rn += ("gatescore_stamp:" + $s) }
  }
}
if(-not (To-Bool $payload.phase4_ok_today)){ $rn += "phase4_ok_today=false" }
if(-not (To-Bool $payload.ev_hard_daily_ok_today)){ $rn += "ev_hard_daily_ok_today=false" }
if(-not (To-Bool $payload.phase23_health_today_row_ok)){ $rn += ("phase23_today_row_missing:last=" + ($payload.phase23_health_last_date + "")) }
if(-not (To-Bool $payload.ev_hard_today_row_ok)){ $rn += ("ev_hard_today_row_missing:last=" + ($payload.ev_hard_last_date + "")) }
if(-not (To-Bool $payload.gatescore_ok_today)){ $rn += "gatescore_ok_today=false" }
if(-not (To-Bool $payload.gatescore_fresh_today)){ $rn += "gatescore_fresh_today=false" }
if(-not (To-Bool $payload.nvda_blockg_ready)){ $rn += "nvda_blockg_ready=false" }

$hs = New-Object System.Collections.Generic.HashSet[string]
$rn2 = New-Object System.Collections.Generic.List[string]
foreach($x in @($rn)){
  $s = ("" + $x).Trim()
  if([string]::IsNullOrWhiteSpace($s)){ continue }
  if($hs.Add($s)){ [void]$rn2.Add($s) }
}
$payload.reasons_not_ready = @($rn2)

# Write once
$payloadJson = $payload | ConvertTo-Json -Depth 6
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($statusPath, $payloadJson, $utf8NoBom)

if ($env:HAT_BLOCKG_QUIET -ne "1") {
  Write-Host "[BLOCK-G] Writing Block-G status stub to $statusPath" -ForegroundColor Cyan
  Write-Host "[BLOCK-G] Status snapshot:" -ForegroundColor Yellow
  $payload.GetEnumerator() | Format-Table -AutoSize
}

exit 0
