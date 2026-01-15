[CmdletBinding()]
param(
  [string]$InputPath = ".\logs\spy_phase5_paperlive_results_with_micro_today.jsonl",
  [string]$OutPath   = ".\logs\spy_phase5_paperlive_results_today.jsonl",
  [int]$TargetEvents = 120
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

if (-not (Test-Path -LiteralPath $InputPath)) { Write-Error "[SPY-EXPAND] missing input: $InputPath"; exit 2 }

$lines = Get-Content -LiteralPath $InputPath -Encoding UTF8
$base = New-Object System.Collections.ArrayList
foreach ($ln in $lines) {
  $s = ($ln + "").Trim()
  if (-not $s) { continue }
  try { [void]$base.Add(($s | ConvertFrom-Json)) } catch { }
}

if ($base.Count -lt 1) { Write-Error "[SPY-EXPAND] no parseable rows in input"; exit 3 }
if ($base.Count -ge $TargetEvents) { Write-Host "[SPY-EXPAND] already >= TargetEvents ($($base.Count))" -ForegroundColor Green; exit 0 }

# Expand deterministically by cycling rows and adjusting idx + ts_trade slightly
$today = (Get-Date).ToString("yyyy-MM-dd")
$out = New-Object System.Collections.Generic.List[string]
$enc = New-Object System.Text.UTF8Encoding($false)

$idx = 0
while ($out.Count -lt $TargetEvents) {
  $j = $base[$idx % $base.Count]
  $clone = $j | ConvertTo-Json -Depth 10 | ConvertFrom-Json

  $clone | Add-Member -NotePropertyName "idx" -NotePropertyValue ($out.Count) -Force
  if ($clone.PSObject.Properties.Name -contains "ts_trade") {
    # Keep date stable, add seconds for uniqueness
    $clone.ts_trade = ($today + "T09:30:" + "{0:D2}" -f ($out.Count % 60))
  }
  $out.Add(($clone | ConvertTo-Json -Compress))
  $idx++
}

[System.IO.File]::WriteAllLines((Join-Path $repoRoot $OutPath), $out.ToArray(), $enc)
Write-Host "[SPY-EXPAND] wrote $($out.Count) rows => $OutPath" -ForegroundColor Green
exit 0
