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
  # CSV missing in your repo right now; use ev_hard_evidence_raw.json
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

# GateScore ok today (conservative): fresh_today + non-empty NVDA events
$payload.gatescore_ok_today = $false
if((To-Bool $payload.gatescore_fresh_today)){
  if(Has-NonEmpty (EventsFileFor $logsDir "NVDA")){
    $payload.gatescore_ok_today = $true
  }
}

# Per-symbol readiness flags (PS-safe; no -and assignments)
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

$payload.spy_blockg_ready = $false
if((To-Bool $payload.gatescore_fresh_today)){
  if(Has-NonEmpty (EventsFileFor $logsDir "SPY")){
    $payload.spy_blockg_ready = $true
  }
}

$payload.qqq_blockg_ready = $false
if((To-Bool $payload.gatescore_fresh_today)){
  if(Has-NonEmpty (EventsFileFor $logsDir "QQQ")){
    $payload.qqq_blockg_ready = $true
  }
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
