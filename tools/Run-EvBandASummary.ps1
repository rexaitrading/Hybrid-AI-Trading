param(
    [string]$PythonExe = ".\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"

Write-Host "[EV-RESEARCH] Using Python: $PythonExe" -ForegroundColor Cyan

# 1) Rebuild CSVs (NVDA / SPY / QQQ)
& $PythonExe tools\nvda_phase5_paper_to_csv.py
& $PythonExe tools\spy_phase5_paper_to_csv.py
& $PythonExe tools\qqq_phase5_paper_to_csv.py

Write-Host "`n[EV-RESEARCH] Band 0/1/2 summary (NVDA / SPY / QQQ)" -ForegroundColor Yellow

# 2) Run the Band summary helper and capture output
$summaryPath = Join-Path (Get-Location) "logs\ev_bandA_summary_latest.txt"

# Capture stdout ONLY into a variable (no 2>&1 here)
$summary = & $PythonExe tools\ev_bandA_summary.py

# Print to console
$summary

# Write the same summary to the log file (overwrite)
$summary | Out-File -FilePath $summaryPath -Encoding UTF8

Write-Host "`n[EV-RESEARCH] Saved latest summary to $summaryPath" -ForegroundColor Cyan