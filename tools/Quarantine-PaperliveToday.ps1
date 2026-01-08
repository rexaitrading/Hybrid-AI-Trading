[CmdletBinding()]
param(
  [ValidateSet("SPY","QQQ","ALL")]
  [string]$Symbol = "ALL"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Canon([string]$p){
  try { return (Resolve-Path -LiteralPath $p -ErrorAction Stop).Path } catch { return $p }
}

function Quarantine-One([string]$sym){
  $s = $sym.ToUpperInvariant()
  $repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
  $logs = Join-Path $repoRoot "logs"
  $path = Join-Path $logs (("{0}_phase5_paperlive_results_with_micro_today.jsonl" -f $s.ToLowerInvariant()))
  if(-not (Test-Path -LiteralPath $path)){
    Write-Host ("[QUAR] {0}: missing => OK (producer not run)" -f $s) -ForegroundColor Yellow
    return
  }

  $info = Get-Item -LiteralPath $path
  $today = (Get-Date).Date
  $isToday = ($info.LastWriteTime.Date -eq $today)

  $tail = Get-Content -LiteralPath $path -Tail 400 -Encoding utf8
  $txt = ($tail -join "`n")

  $hasStub = $false
  if($s -eq "SPY"){
    if($txt -match '"status"\s*:\s*"ok_stub_engine"' -or $txt -match 'SPY_ORB_REPLAY'){ $hasStub = $true }
  } elseif($s -eq "QQQ"){
    if($txt -match 'stub_engine' -or $txt -match 'with_micro_stub_engine_v1'){ $hasStub = $true }
  }

  if((-not $isToday) -or $hasStub){
    $stamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
    $dst = ($path + ".STALE_" + $stamp)
    Move-Item -LiteralPath $path -Destination $dst -Force
    Write-Host ("[QUAR] {0}: quarantined => {1}" -f $s,(Canon $dst)) -ForegroundColor Green
  } else {
    Write-Host ("[QUAR] {0}: OK (today + non-stub)" -f $s) -ForegroundColor Green
  }
}

if($Symbol -eq "ALL"){
  Quarantine-One "SPY"
  Quarantine-One "QQQ"
} else {
  Quarantine-One $Symbol
}

exit 0