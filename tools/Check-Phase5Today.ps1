[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail-Contract([string]$Msg){
  [Console]::Error.WriteLine($Msg)
  exit 2
}
function Fail-Script([string]$Msg){
  [Console]::Error.WriteLine($Msg)
  exit 1
}

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$today = (Get-Date).ToString("yyyy-MM-dd")

# 1) EV-hard daily CSV must include today row with ok==true
$csvPath = Join-Path $repoRoot "logs\phase5_ev_hard_veto_daily.csv"
if(-not (Test-Path $csvPath)){
  Fail-Contract "PHASE5: missing logs/phase5_ev_hard_veto_daily.csv"
}

try{
  $rows = Import-Csv -LiteralPath $csvPath
}catch{
  Fail-Script "PHASE5: failed to parse phase5_ev_hard_veto_daily.csv"
}

# Find today row by as_of_date/date column (flexible)
$hit = $null
foreach($r in $rows){
  $d = $null
  foreach($k in @("as_of_date","date","trading_day")){
    if($r.PSObject.Properties.Name -contains $k){
      $d = [string]$r.$k
      break
    }
  }
  if($d -and $d.Length -ge 10){ $d = $d.Substring(0,10) }
  if($d -eq $today){ $hit = $r; break }
}

if($null -eq $hit){
  Fail-Contract "PHASE5: no today row in phase5_ev_hard_veto_daily.csv (today=$today)"
}

# ok column may be 'ok' or 'passed' or 'computed_pass'
$ok = $false
foreach($k in @("ok","passed","computed_pass","ev_hard_ok_today")){
  if($hit.PSObject.Properties.Name -contains $k){
    $v = [string]$hit.$k
    $vv = $v.Trim().ToLowerInvariant()
    if($vv -in @("1","true","yes","y")){ $ok = $true }
    break
  }
}
if(-not $ok){
  Fail-Contract "PHASE5: EV-hard today row exists but ok flag is FALSE (today=$today)"
}

Write-Host "PHASE5: EV-hard OK today ($today)" -ForegroundColor Green
exit 0
