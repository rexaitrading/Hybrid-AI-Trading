[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$csvPath = 'research\spy_orb_multi_day_sweep.csv'
if (-not (Test-Path $csvPath)) {
    throw "Sweep CSV not found: $csvPath"
}

$rows = Import-Csv $csvPath

# Group by (orb_minutes, tp_r)  compute average EV
$grouped = $rows | Group-Object orb_minutes, tp_r

$best = $null
$bestEV = -999999

foreach ($g in $grouped) {
    $orb = [int]$g.Group[0].orb_minutes
    $tp  = [double]$g.Group[0].tp_r

    $evs = $g.Group | ForEach-Object { [double]$_.ev }
    $meanEV = ($evs | Measure-Object -Average).Average

    if ($meanEV -gt $bestEV) {
        $bestEV = $meanEV
        $best = [PSCustomObject]@{
            ORB_Minutes = $orb
            TP_R        = $tp
            MeanEV      = $meanEV
            Samples     = $g.Count
        }
    }
}

Write-Host "=== BEST ORB CONFIG (SPY ORB) ===" -ForegroundColor Cyan
$best | Format-List