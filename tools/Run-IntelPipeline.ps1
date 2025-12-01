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

# 6) Route error summary
Write-Host ""
Write-Host "[IntelPipeline] STEP 6: Route error summary" -ForegroundColor Cyan

# Route error summary: count route_fail records in logs\paper_route_errors.jsonl over last N hours.
try {
    $routeLogPath  = Join-Path (Get-Location).Path 'logs\paper_route_errors.jsonl'
    $lookbackHours = 24
    $cutoff        = (Get-Date).ToUniversalTime().AddHours(-$lookbackHours)

    if (-not (Test-Path $routeLogPath)) {
        Write-Host "[RouteErrors] No paper_route_errors.jsonl found; 0 events in last $lookbackHours hour(s)." -ForegroundColor Green
    } else {
        $lines = Get-Content $routeLogPath -ErrorAction SilentlyContinue | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

        if (-not $lines -or $lines.Count -eq 0) {
            Write-Host "[RouteErrors] paper_route_errors.jsonl is empty; 0 events in last $lookbackHours hour(s)." -ForegroundColor Green
        } else {
            $records = @()
            foreach ($line in $lines) {
                try {
                    $rec = $line | ConvertFrom-Json -ErrorAction Stop
                    $records += $rec
                } catch {
                    Write-Host "[RouteErrors] WARN: skipping invalid JSON line in paper_route_errors.jsonl" -ForegroundColor Yellow
                }
            }

            if (-not $records -or $records.Count -eq 0) {
                Write-Host "[RouteErrors] No valid route_fail records found; 0 events in last $lookbackHours hour(s)." -ForegroundColor Green
            } else {
                $recent = $records | Where-Object {
                    $_.ts_logged -and ([DateTime]::Parse($_.ts_logged) -ge $cutoff)
                }

                $countRecent = ($recent | Measure-Object).Count

                # Derive a simple risk flag from recent route errors.
                if ($countRecent -gt 0) {
                    $riskFlag  = "CAUTION"
                    $riskColor = "Yellow"
                } else {
                    $riskFlag  = "OK"
                    $riskColor = "Green"
                }

                Write-Host ("[RouteErrors] {0} - {1} route_fail event(s) in last {2} hour(s) (from paper_route_errors.jsonl)" -f $riskFlag, $countRecent, $lookbackHours) -ForegroundColor $riskColor
            }
        }
    }
} catch {
    Write-Host ("[RouteErrors] ERROR while summarizing route errors: {0}" -f $_.Exception.Message) -ForegroundColor Red
}

Write-Host ""
Write-Host "[IntelPipeline] DONE." -ForegroundColor Cyan