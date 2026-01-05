[CmdletBinding()]
param(
  [string]$SnapshotPath = ".\logs\phase2_micro_cost_snapshot.json",
  [string]$FillsPath    = ".\logs\phase2\phase2_fills.jsonl",
  [string]$SummaryPath  = ".\logs\phase2\phase2_summary.json",
  [int]$MinFills = 100
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Fail([string]$Msg){
  Write-Host ("[PHASE2-GATE] FAIL-CLOSED: " + $Msg) -ForegroundColor Red
  exit 2
}

if(-not (Test-Path -LiteralPath $SnapshotPath)){ Fail "Missing snapshot: $SnapshotPath" }
if(-not (Test-Path -LiteralPath $FillsPath)){ Fail "Missing fills: $FillsPath" }
if(-not (Test-Path -LiteralPath $SummaryPath)){ Fail "Missing summary: $SummaryPath" }

# Snapshot must be ok=true
$sn = Get-Content -LiteralPath $SnapshotPath -Encoding utf8 -Raw | ConvertFrom-Json
if(-not $sn.ok){ Fail ("snapshot ok=false reason=" + [string]$sn.reason) }

# Fills must have enough lines
$lines = @(Get-Content -LiteralPath $FillsPath -Encoding utf8)
if($lines.Count -lt $MinFills){ Fail ("Too few fills: " + $lines.Count + " < " + $MinFills) }

# Summary must have avg_cost_bps numeric and > 0
$sm = Get-Content -LiteralPath $SummaryPath -Encoding utf8 -Raw | ConvertFrom-Json
$avg = $null
try { $avg = [double]$sm.avg_cost_bps } catch { Fail "avg_cost_bps missing/invalid" }
if(-not ($avg -gt 0.0)){ Fail ("avg_cost_bps not >0: " + $avg) }

Write-Host ("[PHASE2-GATE] OK fills=" + $lines.Count + " avg_cost_bps=" + $avg) -ForegroundColor Green
exit 0
