[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "ALL",
  [int]$MinEvents = 10
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$today = (Get-Date).ToString("yyyy-MM-dd")

function Run-One([string]$sym){
  $symU = $sym.ToUpper()
  $out = Join-Path $repoRoot ("logs\{0}_gatescore_events.jsonl" -f $symU.ToLower())

  $writer = switch($symU){
    "NVDA" { Join-Path $toolsDir "Write-NvdaGateScoreEventsFromPaperlive.ps1" }
    "SPY"  { Join-Path $toolsDir "Write-SpyGateScoreEventsFromPaperlive.ps1" }
    "QQQ"  { Join-Path $toolsDir "Write-QqqGateScoreEventsFromPaperlive.ps1" }
  }

  if(-not (Test-Path -LiteralPath $writer)){
    Write-Host ("[GS-EVENTS] {0} missing writer: {1}" -f $symU,$writer) -ForegroundColor Red
    return @{sym=$symU; ok=$false; rc=3; reason="missing_writer"; out=$out; rows=0}
  }

  # Writers handle their own input discovery; enforce MinEvents.
  & powershell -NoProfile -ExecutionPolicy Bypass -File $writer -OutPath $out -Mode rewrite -MinEvents $MinEvents | Out-Host
  $rc = $LASTEXITCODE

  $rows = 0
  if(Test-Path -LiteralPath $out){ $rows = @(Get-Content -LiteralPath $out -Encoding utf8).Count }

  $ok = ($rc -eq 0 -and $rows -ge $MinEvents)
  return @{sym=$symU; ok=$ok; rc=$rc; out=$out; rows=$rows}
}

$syms = @()
if($Symbol -eq "ALL"){ $syms = @("NVDA","SPY","QQQ") } else { $syms = @($Symbol) }

$results = @()
foreach($s in $syms){ $results += (Run-One $s) }

$bad = @($results | Where-Object { -not $_.ok })
$payload = [ordered]@{ as_of_date=$today; results=$results; ok=($bad.Count -eq 0); bad=$bad }
$payload | ConvertTo-Json -Depth 6 | Out-Host

if($bad.Count -eq 0){ exit 0 }
exit 2
