[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)][int]$Count = 2
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$logsDir = Join-Path $repoRoot "logs"
if(-not (Test-Path $logsDir)){ New-Item -ItemType Directory -Path $logsDir | Out-Null }

$out = Join-Path $logsDir "paper_trades_spyqqq_stubs.jsonl"

$now = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")

for($i=0; $i -lt $Count; $i++){
  $spy = @{ ts=$now; symbol="SPY"; signal="LONG"; qty=1; price=500.00; edge_ratio=0.25; micro_score=0.50 } | ConvertTo-Json -Compress
  $qqq = @{ ts=$now; symbol="QQQ"; signal="LONG"; qty=1; price=400.00; edge_ratio=0.25; micro_score=0.50 } | ConvertTo-Json -Compress
  Add-Content -Path $out -Value $spy -Encoding utf8
  Add-Content -Path $out -Value $qqq -Encoding utf8
}

Write-Host "[OK] wrote $out (separate stub file; does not modify logs\paper_trades.jsonl)" -ForegroundColor Green
exit 0