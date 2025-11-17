param(
    [string]$TradesPath = "logs\\paper_execs.jsonl",
    [string]$NewsPath   = "logs\\news_events.jsonl",
    [string]$Date       = $(Get-Date).AddDays(-1).ToString("yyyy-MM-dd")  # default = yesterday
)

Write-Host "[Join-NewsAndTrades] Trades: $TradesPath" -ForegroundColor Cyan
Write-Host "[Join-NewsAndTrades] News:   $NewsPath"   -ForegroundColor Cyan
Write-Host "[Join-NewsAndTrades] Date:   $Date"       -ForegroundColor Cyan

if (-not (Test-Path $TradesPath)) {
    Write-Host "[Join-NewsAndTrades] Trades file not found, nothing to do." -ForegroundColor Yellow
    return
}
if (-not (Test-Path $NewsPath)) {
    Write-Host "[Join-NewsAndTrades] News file not found, nothing to do." -ForegroundColor Yellow
    return
}

function Load-JsonLines {
    param(
        [Parameter(Mandatory=$true)][string]$Path
    )
    Get-Content -Path $Path | ForEach-Object {
        if ([string]::IsNullOrWhiteSpace($_)) { return }
        try {
            $_ | ConvertFrom-Json -ErrorAction Stop
        } catch {
            return
        }
    }
}

# 1) load trades for the given date
$trades = Load-JsonLines -Path $TradesPath | Where-Object {
    $_.ts_trade -like "*$Date*"
}

if (-not $trades) {
    Write-Host "[Join-NewsAndTrades] No trades found for $Date in $TradesPath." -ForegroundColor Yellow
    return
}

# distinct symbols traded that day
$symbols = $trades |
    Where-Object { $_.symbol } |
    Select-Object -ExpandProperty symbol -Unique

Write-Host ("[Join-NewsAndTrades] Symbols traded on {0}:" -f $Date) -ForegroundColor Green
$symbols | ForEach-Object { Write-Host "  - $_" }

# 2) load news events for the same date
$news = Load-JsonLines -Path $NewsPath | Where-Object {
    $_.ts_news -like "*$Date*"
}

if (-not $news) {
    Write-Host "[Join-NewsAndTrades] No news events found for $Date in $NewsPath." -ForegroundColor Yellow
    return
}

Write-Host ""
Write-Host "=== Joined View: Trades vs News ===" -ForegroundColor Green

foreach ($sym in $symbols) {
    Write-Host ""
    Write-Host ">>> $sym  (trades + headlines on $Date)" -ForegroundColor Cyan

    $symTrades = $trades | Where-Object { $_.symbol -eq $sym }
    $symNews   = $news   | Where-Object { $_.symbol -eq $sym }

    if ($symTrades) {
        Write-Host "  Trades:" -ForegroundColor DarkGreen
        $symTrades |
            Select-Object ts_trade, side, qty, entry_px, exit_px, pnl_pct |
            Format-Table -AutoSize
    } else {
        Write-Host "  Trades: (none logged for this symbol on this date)" -ForegroundColor DarkYellow
    }

    if ($symNews) {
        Write-Host "  News:" -ForegroundColor DarkGreen
        $symNews |
            Select-Object ts_news, headline, source |
            Format-Table -Wrap -AutoSize
    } else {
        Write-Host "  News: (no headlines mapped for this symbol on this date)" -ForegroundColor DarkYellow
    }
}