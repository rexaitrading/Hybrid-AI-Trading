$ErrorActionPreference = 'Stop'

Set-Location 'C:\Users\rhcy9\OneDrive\文件\HybridAITrading'

function Test-Phase5Csv {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string] $CsvPath,

        [string] $Label = ''
    )

    if (-not (Test-Path -LiteralPath $CsvPath)) {
        Write-Host "❌ Missing CSV: $CsvPath" -ForegroundColor Red
        return
    }

    Write-Host ""
    Write-Host "=== Phase5 sanity check: $Label ===" -ForegroundColor Cyan
    Write-Host "Path: $CsvPath" -ForegroundColor DarkGray

    $rows = Import-Csv -LiteralPath $CsvPath

    if (-not $rows) {
        Write-Host " CSV has 0 rows." -ForegroundColor Yellow
        return
    }

    Write-Host ("Total rows: {0}" -f $rows.Count) -ForegroundColor Green

    Write-Host "`nBy symbol:" -ForegroundColor Cyan
    $rows |
        Group-Object -Property symbol |
        Sort-Object -Property Name |
        ForEach-Object {
            "{0,5}  {1,5} rows" -f $_.Name, $_.Count
        } | Write-Host

    if ($rows[0].PSObject.Properties.Name -contains 'phase5_sim_allow') {
        Write-Host "`nBy phase5_sim_allow:" -ForegroundColor Cyan
        $rows |
            Group-Object -Property phase5_sim_allow |
            Sort-Object -Property Name |
            ForEach-Object {
                "{0,10}  {1,5} rows" -f ($_.Name -replace '^\s*$', '<empty>'), $_.Count
            } | Write-Host
    }
    else {
        Write-Host "`n(no phase5_sim_allow column found in this CSV)" -ForegroundColor Yellow
    }

    Write-Host "`nSample rows (first 5):" -ForegroundColor Cyan
    $rows | Select-Object -First 5 symbol, ts_trade, side, qty, entry_px, phase5_sim_allow |
        Format-Table -AutoSize
}

Write-Host "=== Phase5 logs inventory ===" -ForegroundColor Cyan
Get-ChildItem -Path 'logs' -File |
    Where-Object { $_.Name -match 'phase5' } |
    Sort-Object Name |
    Format-Table Name, Length, LastWriteTime -AutoSize

Write-Host "`n=== NVDA Phase5 sanity ===" -ForegroundColor Cyan
Test-Phase5Csv -CsvPath 'logs\nvda_phase5_replay_gated.csv' -Label 'NVDA B+ Phase5'

Write-Host "`n=== SPY Phase5 CSV (if present) ===" -ForegroundColor Cyan
Test-Phase5Csv -CsvPath 'logs\spy_phase5_trades.csv' -Label 'SPY Phase5 Trades (paper)'

Write-Host "`n=== SPY/QQQ replay files presence check ===" -ForegroundColor Cyan
Get-ChildItem -Path . -Recurse -File |
    Where-Object { $_.Name -match 'spy' -and $_.Name -match 'replay' -and $_.Extension -eq '.csv' } |
    Sort-Object FullName |
    Format-Table FullName

Get-ChildItem -Path . -Recurse -File |
    Where-Object { $_.Name -match 'qqq' -and $_.Name -match 'replay' -and $_.Extension -eq '.csv' } |
    Sort-Object FullName |
    Format-Table FullName