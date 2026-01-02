[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "ALL",

  [int]$MinEvents = 1
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsDir  = Join-Path $repoRoot "logs"
$today    = (Get-Date).ToString("yyyy-MM-dd")

function Pick([string]$sym){
  $p = & (Join-Path $toolsDir "Pick-TodayPaperliveSource.ps1") -Symbol $sym -LogsDir $logsDir
  $rc = $LASTEXITCODE
  if($rc -ne 0){ return $null }
  $s = ("" + $p).Trim()
  if([string]::IsNullOrWhiteSpace($s)){ return $null }
  return $s
}

function Run-One([string]$sym){
  $symU = $sym.ToUpper()
  $pick = Pick $symU
  if(-not $pick){
    Write-Host ("[GS-EVENTS] {0} no today source (picker rc!=0)" -f $symU) -ForegroundColor Red
    return @{sym=$symU; ok=$false; reason="no_today_source"; input=""; rows=0}
  }
  if(-not (Test-Path -LiteralPath $pick)){
    Write-Host ("[GS-EVENTS] {0} missing input: {1}" -f $symU,$pick) -ForegroundColor Red
    return @{sym=$symU; ok=$false; reason="missing_input"; input=$pick; rows=0}
  }

  $out = Join-Path $logsDir ("{0}_gatescore_events.jsonl" -f $symU.ToLower())

  $writer = switch($symU){
    "NVDA" { Join-Path $toolsDir "Write-NvdaGateScoreEventsFromPaperlive.ps1" }
    "SPY"  { Join-Path $toolsDir "Write-SpyGateScoreEventsFromPaperlive.ps1" }
    "QQQ"  { Join-Path $toolsDir "Write-QqqGateScoreEventsFromPaperlive.ps1" }
  }

  if(-not (Test-Path -LiteralPath $writer)){
    Write-Host ("[GS-EVENTS] {0} missing writer: {1}" -f $symU,$writer) -ForegroundColor Red
    return @{sym=$symU; ok=$false; reason="missing_writer"; input=$pick; rows=0}
  }

  # Tighten-only: never fabricate; pass through writer which already ignores synthetic.
  & powershell -NoProfile -ExecutionPolicy Bypass -File $writer -InputPath $pick -OutPath $out -Mode rewrite -MinEvents $MinEvents | Out-Host
  $rc = $LASTEXITCODE

  $rows = 0
  if(Test-Path -LiteralPath $out){
    $rows = @(Get-Content -LiteralPath $out -Encoding utf8).Count
  }

  return @{sym=$symU; ok=($rc -eq 0); rc=$rc; input=$pick; out=$out; rows=$rows}
}

$syms = @()
if($Symbol -eq "ALL"){ $syms = @("NVDA","SPY","QQQ") } else { $syms = @($Symbol) }

$results = @()
foreach($s in $syms){ $results += (Run-One $s) }

# Fail-closed if any required symbol has 0 rows OR rc != 0
$bad = @($results | Where-Object { (-not $_.ok) -or ($_.rows -lt 1) })
$payload = [ordered]@{
  as_of_date = $today
  results = $results
  ok = ($bad.Count -eq 0)
  bad = $bad
}
$payload | ConvertTo-Json -Depth 6 | Out-Host

if($bad.Count -eq 0){ exit 0 }
exit 2
