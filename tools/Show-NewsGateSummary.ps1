param(
    [string]$GatePath = "logs\\news_gate.jsonl",
    [string]$Date     = $(Get-Date).AddDays(-1).ToString("yyyy-MM-dd"),  # default = yesterday
    [string[]]$Symbols = @("SPY","QQQ","TSX","BITCOIN","BTCUSD")
)

Write-Host "[Show-NewsGateSummary] Gate: $GatePath" -ForegroundColor Cyan
Write-Host "[Show-NewsGateSummary] Date: $Date"     -ForegroundColor Cyan
Write-Host "[Show-NewsGateSummary] Watchlist: $($Symbols -join ', ')" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $GatePath)) {
    Write-Host "[Show-NewsGateSummary] Gate file not found, nothing to show." -ForegroundColor Yellow
    return
}

function Load-JsonLines {
    param([string]$Path)
    Get-Content -Path $Path | ForEach-Object {
        if ([string]::IsNullOrWhiteSpace($_)) { return }
        try {
            $_ | ConvertFrom-Json -ErrorAction Stop
        } catch { return }
    }
}

$all = Load-JsonLines -Path $GatePath | Where-Object {
    $_.date -eq $Date
}

if (-not $all) {
    Write-Host "[Show-NewsGateSummary] No gate records for $Date." -ForegroundColor Yellow
    return
}

# Filter to watchlist if provided
if ($Symbols -and $Symbols.Count -gt 0) {
    $rows = $all | Where-Object { $_.symbol -in $Symbols }
} else {
    $rows = $all
}

if (-not $rows) {
    Write-Host "[Show-NewsGateSummary] No matching symbols in gate for $Date." -ForegroundColor Yellow
    return
}

Write-Host "=== News Gate Summary ($Date) ===" -ForegroundColor Green

$rows |
    Sort-Object symbol |
    Select-Object symbol, news_count, neg_count, pos_count, news_score, risk_flag |
    Format-Table -AutoSize