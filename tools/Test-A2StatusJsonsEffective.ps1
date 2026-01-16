[CmdletBinding()]
param(
  [string[]]$Markets = @("US","HK","JP","SG","IN","KR","TW"),
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Resolve-RepoRoot(){
  $toolsDir = Split-Path -Parent $PSCommandPath
  $rr = Split-Path -Parent $toolsDir
  try { return (Resolve-Path -LiteralPath $rr -ErrorAction Stop).Path } catch { return $rr }
}
$repoRoot = Resolve-RepoRoot

function Get-MarketLogsDir([string]$Market){
  try{
    $p = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1") -Market $Market
    if($p){ return $p }
  } catch { }
  return (Join-Path $repoRoot ("logs\{0}" -f $Market))
}

function Slice10([string]$d){
  $s = ([string]$d).Trim()
  if($s.Length -ge 10){ return $s.Substring(0,10) }
  return $s
}

function Read-Json([string]$Path){
  if(-not (Test-Path -LiteralPath $Path)){ return $null }
  try { return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json) } catch { return $null }
}

function EffectiveOk([string]$StatusPath,[string]$TodayLocal){
  $j = Read-Json $StatusPath
  if(-not $j){ return $null }
  $asOf=""; if($j.PSObject.Properties.Name -contains "as_of_date"){ $asOf = Slice10 ([string]$j.as_of_date) }
  $ok=$false; if($j.PSObject.Properties.Name -contains "ok_today"){ $ok=[bool]$j.ok_today }
  return (($asOf -eq $TodayLocal) -and $ok)
}

$builder = Join-Path $repoRoot "tools\Build-BlockGStatusStub.ps1"
if(-not (Test-Path -LiteralPath $builder)){ throw "[FAIL-CLOSED] Missing builder: $builder" }

$fail = $false
foreach($m in $Markets){
  $logsDir = Get-MarketLogsDir $m
  if(-not (Test-Path -LiteralPath $logsDir)){ New-Item -ItemType Directory -Force -Path $logsDir | Out-Null }

  # Build stub
  $env:HAT_MARKET=$m; $env:HAT_SYMBOL=$Symbol
  & $builder -Market $m -Symbol $Symbol | Out-Null

  $stubPath = Join-Path $logsDir "blockg_status_stub.json"
  if(-not (Test-Path -LiteralPath $stubPath)){
    Write-Host ("[A2] FAIL market={0} missing stub {1}" -f $m,$stubPath) -ForegroundColor Red
    $fail = $true
    continue
  }

  $stub = Read-Json $stubPath
  if(-not $stub){
    Write-Host ("[A2] FAIL market={0} stub parse failed {1}" -f $m,$stubPath) -ForegroundColor Red
    $fail = $true
    continue
  }

  $todayLocal = Slice10 ([string]$stub.as_of_date)

  # Effective status booleans
  $p4Path  = Join-Path $logsDir "phase4_status.json"
  $p23Path = Join-Path $logsDir "phase23_status.json"
  $evPath  = Join-Path $logsDir "ev_hard_status.json"

  $p4Eff  = EffectiveOk $p4Path  $todayLocal
  $p23Eff = EffectiveOk $p23Path $todayLocal
  $evEff  = EffectiveOk $evPath  $todayLocal

  # Compare to stub fields
  $okP4  = [bool]$stub.phase4_ok_today
  $okP23 = [bool]$stub.phase23_health_ok_today
  $okEv  = [bool]$stub.ev_hard_daily_ok_today

  Write-Host ("[A2] market={0} todayLocal={1} P4eff={2} P23eff={3} EVeff={4} | stub P4={5} P23={6} EV={7}" -f $m,$todayLocal,$p4Eff,$p23Eff,$evEff,$okP4,$okP23,$okEv)

  if(($null -ne $p4Eff)  -and ($okP4  -ne [bool]$p4Eff)){  Write-Host ("[A2] FAIL market={0} phase4 mismatch" -f $m) -ForegroundColor Red; $fail=$true }
  if(($null -ne $p23Eff) -and ($okP23 -ne [bool]$p23Eff)){ Write-Host ("[A2] FAIL market={0} phase23 mismatch" -f $m) -ForegroundColor Red; $fail=$true }
  if(($null -ne $evEff)  -and ($okEv  -ne [bool]$evEff)){  Write-Host ("[A2] FAIL market={0} ev_hard mismatch" -f $m) -ForegroundColor Red; $fail=$true }
}

if($fail){
  throw "[FAIL-CLOSED] A2 effective status audit failed"
}

Write-Host "[A2] OK: effective status audit passed" -ForegroundColor Green
exit 0

