[CmdletBinding()]
param(
  [ValidateSet("SPY","QQQ")]
  [string]$Symbol,
  [string]$OutPath = "",
  [int]$N = 10
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

$today = ((($env:HAT_ASOF_DATE + "")).Trim())
if($today){
  if($today.Length -ge 10){ $today = $today.Substring(0,10) }
  if($today -notmatch '^\d{4}-\d{2}-\d{2}$'){ throw ("[FAIL-CLOSED] HAT_ASOF_DATE not yyyy-MM-dd: " + $today) }
} else {
  $today = (Get-Date).ToString("yyyy-MM-dd")
}
if (-not $OutPath) { $OutPath = ".\logs\{0}_gatescore_events.jsonl" -f $Symbol.ToLowerInvariant() }

$enc = New-Object System.Text.UTF8Encoding($false)
$lines = New-Object System.Collections.Generic.List[string]
for ($i=1; $i -le $N; $i++) {
  $edge = if ($Symbol -eq "SPY") { 0.01 } else { 0.01 }
  $micro = 0.2
  $obj = [ordered]@{
    as_of_date = $today
    symbol = $Symbol
    source = "STUB"
    score = $edge
    edge_ratio = $edge
    micro_score = $micro
    micro_score_source = "stub"
    realized_pnl = 0
    count_signals = 1
    pnl_samples = 1
    notes = "stub_event"
  }
  $lines.Add(($obj | ConvertTo-Json -Compress))
}

$dir = Split-Path -Parent $OutPath
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
if([System.IO.Path]::IsPathRooted($OutPath)){ $outFull = $OutPath } else { $outFull = (Join-Path $repoRoot $OutPath) }
$dir2 = Split-Path -Parent $outFull
if($dir2 -and -not (Test-Path -LiteralPath $dir2)) { New-Item -ItemType Directory -Force -Path $dir2 | Out-Null }
[System.IO.File]::WriteAllLines($outFull, $lines.ToArray(), $enc)

Write-Host "[GS-STUB] wrote $($lines.Count) events => $OutPath symbol=$Symbol date=$today" -ForegroundColor Green
exit 0
