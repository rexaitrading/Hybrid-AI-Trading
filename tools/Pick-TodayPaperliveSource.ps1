[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol,
  [string]$LogsDir = ".\logs"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$today = (Get-Date).ToString("yyyy-MM-dd")
$logs = (Resolve-Path -LiteralPath $LogsDir).Path

$lower = $Symbol.ToLower()
$symU  = $Symbol.ToUpper()

$candidates = @(
  (Join-Path $logs ("paper_live_{0}_{1}.jsonl" -f $symU, $today)),
  (Join-Path $logs ("{0}_phase5_paperlive_results_with_micro_today.jsonl" -f $lower)),
  (Join-Path $logs ("{0}_phase5_paperlive_results_today.jsonl" -f $lower)),
  (Join-Path $logs ("{0}_phase5_paperlive_results.jsonl" -f $lower))
)

function Get-AsOf([string]$ln){
  if($ln -match '"as_of_date"\s*:\s*"([^"]+)"'){ return $matches[1].Substring(0,10) }
  return ""
}
function Get-TsTrade([string]$ln){
  if($ln -match '"ts_trade"\s*:\s*"([^"]+)"'){ return $matches[1].Substring(0,10) }
  return ""
}

foreach($p in $candidates){
  if(-not (Test-Path -LiteralPath $p)){ continue }
  if((Get-Item -LiteralPath $p).Length -le 0){ continue }

  foreach($ln in (Get-Content -LiteralPath $p -Encoding utf8)){
    if([string]::IsNullOrWhiteSpace($ln)){ continue }
    $d1 = Get-AsOf $ln
    $d2 = Get-TsTrade $ln
    if($d1 -eq $today -or $d2 -eq $today){
      Write-Output $p
      exit 0
    }
  }
}

Write-Host ("[PICK-TODAY] No qualifying TODAY source found for {0} in {1}" -f $Symbol,$logs) -ForegroundColor Red
exit 2
