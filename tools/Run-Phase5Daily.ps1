$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "`n[DAILY] Phase-5 micro sessions + CSV + LIVE audit + summary" -ForegroundColor Cyan

# 1) Run all micro sessions + CSV + LIVE audit
.\tools\Run-Phase5AllMicroSessions.ps1

# 2) Capture LIVE summary into a dated log
$summaryLogDir = Join-Path $repoRoot "logs"
if (-not (Test-Path $summaryLogDir)) {
    New-Item -ItemType Directory -Path $summaryLogDir | Out-Null
}

$today = Get-Date -Format "yyyyMMdd"
$logPath = Join-Path $summaryLogDir ("phase5_live_summary_{0}.txt" -f $today)

Write-Host ("`n[DAILY] Writing summary to {0}" -f $logPath) -ForegroundColor Yellow

# Run the summary and capture output
$summaryOutput = & .\tools\Phase5_LiveSummary.ps1 2>&1
$summaryOutput | Out-File -FilePath $logPath -Encoding UTF8

Write-Host "`n[DAILY] Phase-5 daily run completed." -ForegroundColor Green
