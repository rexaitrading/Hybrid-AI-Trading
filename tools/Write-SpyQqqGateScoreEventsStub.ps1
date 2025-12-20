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

$today = (Get-Date).ToString("yyyy-MM-dd")
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
    realized_pnl = "0"
    count_signals = 1
    pnl_samples = 1
    notes = "stub_event"
  }
  $lines.Add(($obj | ConvertTo-Json -Compress))
}

$dir = Split-Path -Parent $OutPath
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
[System.IO.File]::WriteAllLines((Join-Path $repoRoot $OutPath), $lines.ToArray(), $enc)

Write-Host "[GS-STUB] wrote $($lines.Count) events => $OutPath symbol=$Symbol date=$today" -ForegroundColor Green
exit 0