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

# stdout marker for pytest subprocess capture
Write-Output ("blockg_status_stub.json -> " + $statusPath)

# ---- helpers ----
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

# ---- build payload (fail-closed) ----
$asOf = Effective-AsofDate $logsDir
$payload = [ordered]@{
  as_of_date = $asOf

  gatescore_as_of_date = ""
  gatescore_fresh_for_session = $false
  gatescore_fresh_today = $false

  phase23_health_ok_today = $false
  ev_hard_daily_ok_today  = $false
  phase4_ok_today         = $false
  gatescore_ok_today      = $false
  nvda_blockg_ready       = $false

  reasons_not_ready = @()
}

# ---- GateScore session date + recency ----
try {
  $gs = Join-Path $logsDir "gatescore_daily_summary.csv"
  if(Test-Path -LiteralPath $gs){
    $rows = @(Import-Csv $gs)
    if($rows.Count -gt 0){
      $last = $rows[-1]
      $gsAsOf = (($last.as_of_date + "").Trim())
      if($gsAsOf){
        $payload.gatescore_as_of_date = $gsAsOf
        $payload.gatescore_fresh_for_session = ($gsAsOf -eq $asOf)
      }
    }
  }
} catch {}

# ---- Institutional freshness invariant (test asserts this) ----
if(($payload.gatescore_as_of_date + "") -eq ""){
  $payload.gatescore_fresh_for_session = $false
  $payload.gatescore_fresh_today = $false
} elseif(($payload.gatescore_as_of_date + "") -eq ($payload.as_of_date + "")){
  $payload.gatescore_fresh_today = (To-Bool $payload.gatescore_fresh_for_session)
} else {
  $payload.gatescore_fresh_today = $false
}

# ---- reasons (canonical tail) ----
$rn = @()
if(-not (To-Bool $payload.phase23_health_ok_today)){ $rn += "phase23_health_ok_today=false" }
if(-not (To-Bool $payload.ev_hard_daily_ok_today)){ $rn += "ev_hard_daily_ok_today=false" }
if(-not (To-Bool $payload.phase4_ok_today)){ $rn += "phase4_ok_today=false" }
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

# ---- write once UTF-8 no BOM ----
$payloadJson = $payload | ConvertTo-Json -Depth 6
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($statusPath, $payloadJson, $utf8NoBom)

if ($env:HAT_BLOCKG_QUIET -ne "1") {
  Write-Host "[BLOCK-G] Writing Block-G status stub to $statusPath" -ForegroundColor Cyan
  Write-Host "[BLOCK-G] Status snapshot:" -ForegroundColor Yellow
  $payload.GetEnumerator() | Format-Table -AutoSize
}

exit 0
