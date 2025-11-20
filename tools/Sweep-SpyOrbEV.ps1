[CmdletBinding()]
param(
    # ORB windows to test
    [int[]]$OrbWindows = @(5, 15, 30),

    # TP multiples to test
    [double[]]$TpRValues = @(1.5, 2.0, 2.5),

    # Max number of dates to sweep (0 = all)
    [int]$MaxDates = 0
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptRoot = $PSScriptRoot
$repoRoot   = Split-Path -Parent $scriptRoot

Set-Location $repoRoot

$csvOut = 'research\spy_orb_multi_day_sweep.csv'
"date,orb_minutes,tp_r,trades,win_rate,ev,mean_pnl_pct,mean_r" | Out-File $csvOut -Encoding utf8

# Gather unique dates from SPY_1m.csv
$dates = Import-Csv 'data\SPY_1m.csv' |
    Select-Object timestamp |
    ForEach-Object { ($_.timestamp -split 'T')[0] } |
    Sort-Object -Unique

if ($MaxDates -gt 0) {
    $dates = $dates | Select-Object -First $MaxDates
}

foreach ($d in $dates) {
    $dateObj = [DateTime]::ParseExact($d,'yyyy-MM-dd',$null)
    $DateTag = $dateObj.ToString('yyyyMMdd')

    foreach ($orb in $OrbWindows) {
        foreach ($tp in $TpRValues) {

            $jsonl = "replay_out\spy_orb_trades_{0}_orb{1}_tp{2}.jsonl" -f $DateTag, $orb, $tp

            & '.\tools\Run-SpyOrbReplay.ps1' -DateTag $DateTag -OrbMinutes $orb -TpR $tp

            if (-not (Test-Path $jsonl)) {
                continue
            }

            # Force array so Length is always valid under StrictMode
            [array]$tradeLines = Get-Content $jsonl
            if ($tradeLines.Length -eq 0) {
                $row = "$d,$orb,$tp,0,0,0,0,0"
                Add-Content $csvOut $row
                continue
            }

            # Convert each JSON line to an object and force array
            [array]$trades = $tradeLines | ForEach-Object { $_ | ConvertFrom-Json }

            $count = $trades.Length
            if ($count -eq 0) {
                $row = "$d,$orb,$tp,0,0,0,0,0"
                Add-Content $csvOut $row
                continue
            }

            # Force the Where-Object result into an array, then use .Count
            $wins    = @($trades | Where-Object { $_.outcome -eq 'TP' }).Count
            $winRate = $wins / $count

            $meanPnl = ($trades | Measure-Object -Property gross_pnl_pct -Average).Average
            $meanR   = ($trades | Measure-Object -Property r_multiple     -Average).Average

            # Simple EV: winRate * meanR - (1 - winRate) * 1R loss
            $ev = ($winRate * $meanR) - ((1.0 - $winRate) * 1.0)

            $row = "$d,$orb,$tp,$count,$winRate,$ev,$meanPnl,$meanR"
            Add-Content $csvOut $row
        }
    }
}

Write-Host "SPY ORB multi-day sweep completed." -ForegroundColor Green
Write-Host "Output CSV: $csvOut" -ForegroundColor Green