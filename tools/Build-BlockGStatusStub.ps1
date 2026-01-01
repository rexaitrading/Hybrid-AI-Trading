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
$payload = [ordered]@{
  as_of_date = $asOf

  gatescore_as_of_date = ""
  gatescore_fresh_for_session = $false
  gatescore_fresh_today = $false
  gatescore_ok_today = $false

  phase4_ok_today = $false
  ev_hard_daily_ok_today = $false

  nvda_blockg_ready = $false
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

# GateScore ok today (quality):
# - NVDA fallback: use stub events file if NVDA row missing in daily_summary
# - SPY/QQQ: use daily_summary thresholds/samples

# NVDA GateScore OK (fallback path)
$payload.gatescore_ok_today = $false
if((To-Bool $payload.gatescore_fresh_today)){
  $nvRow = Get-GateScoreRow $logsDir "NVDA" $asOf
  if($null -ne $nvRow){
    if(GateScoreOkFromRow $nvRow){ $payload.gatescore_ok_today = $true }
  } else {
    # fallback to stub events presence (nvda_gatescore_events.jsonl may be empty)
    if(Has-NonEmpty (EventsFileFor $logsDir "NVDA")){ $payload.gatescore_ok_today = $true }
  }
}

# NVDA readiness (PS-safe; no -and operators)
$payload.nvda_blockg_ready = $false
if((To-Bool $payload.phase4_ok_today)){
  if((To-Bool $payload.ev_hard_daily_ok_today)){
    if((To-Bool $payload.gatescore_ok_today)){
      if((To-Bool $payload.gatescore_fresh_today)){
        $payload.nvda_blockg_ready = $true
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
if(-not (To-Bool $payload.phase4_ok_today)){ $rn += "phase4_ok_today=false" }
if(-not (To-Bool $payload.ev_hard_daily_ok_today)){ $rn += "ev_hard_daily_ok_today=false" }
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