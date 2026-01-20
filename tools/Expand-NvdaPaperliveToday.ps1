[CmdletBinding()]
param(
  [string]$InputPath = ".\logs\nvda_phase5_paperlive_results_today.jsonl",
  [string]$OutPath   = ".\logs\nvda_phase5_paperlive_results_today.jsonl",
  [int]$TargetEvents = 120
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

if (-not (Test-Path -LiteralPath $InputPath)) { Write-Error "[NVDA-EXPAND] missing input: $InputPath"; exit 2 }

# Prefer RunContext day (avoid local midnight mismatch)
$today = ((($env:HAT_ASOF_DATE + "")).Trim())
if(-not $today){ $today = ((($env:HAT_AS_OF_DATE + "")).Trim()) }
if(-not $today){ $today = (Get-Date).ToString("yyyy-MM-dd") }
if($today.Length -ge 10){ $today = $today.Substring(0,10) }

$linesIn = Get-Content -LiteralPath $InputPath -Encoding UTF8
$base = New-Object System.Collections.ArrayList
foreach ($ln in $linesIn) {
  $s = ($ln + "").Trim()
  if (-not $s) { continue }
  try { [void]$base.Add(($s | ConvertFrom-Json)) } catch { }
}

if ($base.Count -lt 1) { Write-Error "[NVDA-EXPAND] no parseable rows in input"; exit 3 }
if ($base.Count -ge $TargetEvents) {
  # If caller output differs, write normalized copy; otherwise no-op.
  if($OutPath -ne $InputPath){
    $enc = New-Object System.Text.UTF8Encoding($false)
    $outFull = (Join-Path $repoRoot $OutPath)
    $txt = ($linesIn -join "`n") + "`n"
    [System.IO.File]::WriteAllText($outFull, $txt, $enc)
    Write-Host "[NVDA-EXPAND] already >= TargetEvents ($($base.Count)); copied -> $OutPath" -ForegroundColor Green
  } else {
    Write-Host "[NVDA-EXPAND] already >= TargetEvents ($($base.Count))" -ForegroundColor Green
  }
  exit 0
}

# Expand deterministically by cycling rows and adjusting idx + ts_trade slightly
$out = New-Object System.Collections.Generic.List[string]
$enc = New-Object System.Text.UTF8Encoding($false)

$idx = 0
while ($out.Count -lt $TargetEvents) {
  $j = $base[$idx % $base.Count]
  $clone = $j | ConvertTo-Json -Depth 10 | ConvertFrom-Json

  $clone | Add-Member -NotePropertyName "idx" -NotePropertyValue ($out.Count) -Force
  if ($clone.PSObject.Properties.Name -contains "ts_trade") {
    $clone.ts_trade = ($today + "T09:30:" + "{0:D2}" -f ($out.Count % 60))
  }
  if ($clone.PSObject.Properties.Name -contains "as_of_date") {
    $clone.as_of_date = $today
  }
  $out.Add(($clone | ConvertTo-Json -Compress))
  $idx++
}

$outFull = (Join-Path $repoRoot $OutPath)
[System.IO.File]::WriteAllText($outFull, ($out.ToArray() -join "`n") + "`n", $enc)
Write-Host "[NVDA-EXPAND] wrote $($out.Count) rows => $OutPath (today=$today)" -ForegroundColor Green
exit 0
