param(
    [string]$SpyCsv  = "logs/spy_phase5_orb_phase5_risk.csv",
    [string]$QqqCsv  = "logs/qqq_phase5_orb_phase5_risk.csv",
    [string]$NvdaCsv = "logs/nvda_phase5_orb_phase5_risk.csv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "[PHASE-5] Option A - ORB multi-symbol risk sanity (SPY / QQQ / NVDA)" -ForegroundColor Cyan

function Get-Phase5SummaryFromCsv {
    param(
        [string]$Symbol,
        [string]$CsvPath
    )

    if (-not (Test-Path $CsvPath)) {
        Write-Host "  [$Symbol] MISSING CSV: $CsvPath" -ForegroundColor Red
        return $null
    }

    $rows = @(Import-Csv $CsvPath)
    if ($rows.Count -eq 0) {
        Write-Host "  [$Symbol] CSV has 0 rows: $CsvPath" -ForegroundColor DarkYellow
        return $null
    }

    $props = $rows[0].PSObject.Properties.Name

    # Choose Phase-5 flag column (combined preferred)
    $flagProp = $null
    if ($props -contains "phase5_combined_allowed") {
        $flagProp = "phase5_combined_allowed"
    } elseif ($props -contains "phase5_allowed") {
        $flagProp = "phase5_allowed"
    }

    $allowedCount = $null
    $blockedCount = $null
    if ($flagProp) {
        $grouped      = $rows | Group-Object $flagProp
        $allowedGroup = $grouped | Where-Object { $_.Name -eq "True" }
        $blockedGroup = $grouped | Where-Object { $_.Name -eq "False" }

        $allowedCount = if ($allowedGroup) { $allowedGroup.Count } else { 0 }
        $blockedCount = if ($blockedGroup) { $blockedGroup.Count } else { 0 }
    }

    # r_multiple stats (if present)
    $avgR = $null
    $minR = $null
    $maxR = $null

    if ($props -contains "r_multiple") {
        $rStats = $rows |
            Where-Object { $_.r_multiple -ne "" } |
            Select-Object @{Name="r_multiple";Expression={[double]$_.r_multiple}} |
            Measure-Object -Property r_multiple -Average -Minimum -Maximum

        $avgR = [math]::Round($rStats.Average, 3)
        $minR = [math]::Round($rStats.Minimum, 3)
        $maxR = [math]::Round($rStats.Maximum, 3)
    }

    [PSCustomObject]@{
        symbol            = $Symbol
        trades            = $rows.Count
        allowed_trades    = $allowedCount
        blocked_trades    = $blockedCount
        avg_r_multiple    = $avgR
        min_r_multiple    = $minR
        max_r_multiple    = $maxR
        flag_column_used  = $flagProp
        has_r_multiple    = ($props -contains "r_multiple")
    }
}

$results = @()
$results += Get-Phase5SummaryFromCsv -Symbol "SPY"  -CsvPath $SpyCsv
$results += Get-Phase5SummaryFromCsv -Symbol "QQQ"  -CsvPath $QqqCsv
$results += Get-Phase5SummaryFromCsv -Symbol "NVDA" -CsvPath $NvdaCsv

Write-Host ""
Write-Host "[PHASE-5] ORB multi-symbol summary:" -ForegroundColor Cyan

$results |
    Where-Object { $_ -ne $null } |
    Sort-Object symbol |
    Format-Table symbol, trades, allowed_trades, blocked_trades, avg_r_multiple, min_r_multiple, max_r_multiple, flag_column_used, has_r_multiple -AutoSize

Write-Host ""
Write-Host "[PHASE-5] Option A sanity complete." -ForegroundColor Green