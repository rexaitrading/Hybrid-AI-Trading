param(
    [string]$Date = $(Get-Date).AddDays(-1).ToString("yyyy-MM-dd")  # default = yesterday
)

Write-Host "=== Run-IntelPipeline.ps1 ===" -ForegroundColor Cyan
Write-Host "Repo:  $((Get-Location).Path)" -ForegroundColor DarkCyan
Write-Host "Date:  $Date (for gate + join)" -ForegroundColor DarkCyan
Write-Host ""

$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "[IntelPipeline] Python venv not found at $py" -ForegroundColor Red
    return
}

# 1) Raw ingestion
Write-Host "[IntelPipeline] STEP 1: Raw ingestion (news + YouTube)" -ForegroundColor Cyan
& $py tools\news_feed.py
Write-Host "[IntelPipeline] news_feed.py completed." -ForegroundColor Green

& $py tools\yt_scalper_feed.py
Write-Host "[IntelPipeline] yt_scalper_feed.py completed." -ForegroundColor Green

# 2) Normalization
Write-Host ""
Write-Host "[IntelPipeline] STEP 2: Normalization" -ForegroundColor Cyan
.\tools\Collect-NewsEvents.ps1
.\tools\Collect-PaperExecs.ps1
.\tools\Collect-RouteErrors.ps1

# 3) Build news gates
Write-Host ""
Write-Host "[IntelPipeline] STEP 3: Build news gates" -ForegroundColor Cyan
.\tools\Build-NewsGate.ps1 -Date $Date

# 4) Joined intel (trades vs news)
Write-Host ""
Write-Host "[IntelPipeline] STEP 4: Join trades vs news (if trades exist on date)" -ForegroundColor Cyan
.\tools\Join-NewsAndTrades.ps1 -Date $Date

# 5) News gate summary
Write-Host ""
Write-Host "[IntelPipeline] STEP 5: Show news gate summary" -ForegroundColor Cyan
.\tools\Show-NewsGateSummary.ps1 -Date $Date

Write-Host ""
Write-Host "[IntelPipeline] DONE." -ForegroundColor Cyan
