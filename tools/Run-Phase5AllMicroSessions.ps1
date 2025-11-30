$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "`n[PHASE5] Run ALL Phase-5 micro sessions + CSV + LIVE audit" -ForegroundColor Cyan

$PythonExe      = ".\.venv\Scripts\python.exe"
$env:PYTHONPATH = (Join-Path (Get-Location) "src")

function Run-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )
    Write-Host "`n[STEP] $Name" -ForegroundColor Yellow
    & $Action
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Step '$Name' failed with code $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

# 1) Live micro sessions (NVDA / SPY / QQQ)
Run-Step -Name "NVDA Phase-5 micro session" -Action { .\tools\Run-NVDA-Phase5MicroSession.ps1 }
Run-Step -Name "SPY Phase-5 micro session"  -Action { .\tools\Run-SPY-Phase5MicroSession.ps1 }
Run-Step -Name "QQQ Phase-5 micro session"  -Action { .\tools\Run-QQQ-Phase5MicroSession.ps1 }

# 2) Re-generate CSVs from JSONL
Run-Step -Name "Convert NVDA JSONL -> CSV" -Action { & $PythonExe "tools\nvda_phase5_paper_to_csv.py" }
Run-Step -Name "Convert SPY JSONL -> CSV"  -Action { & $PythonExe "tools\spy_phase5_paper_to_csv.py" }
Run-Step -Name "Convert QQQ JSONL -> CSV"  -Action { & $PythonExe "tools\qqq_phase5_paper_to_csv.py" }

# 3) Add origin = LIVE to all three CSVs
Run-Step -Name "Add origin=LIVE to NVDA CSV" -Action { .\tools\Phase5_AddOriginToCsv.ps1 -CsvPath "logs\nvda_phase5_paper_for_notion.csv" -Origin "LIVE" }
Run-Step -Name "Add origin=LIVE to SPY CSV"  -Action { .\tools\Phase5_AddOriginToCsv.ps1 -CsvPath "logs\spy_phase5_paper_for_notion.csv" -Origin "LIVE" }
Run-Step -Name "Add origin=LIVE to QQQ CSV"  -Action { .\tools\Phase5_AddOriginToCsv.ps1 -CsvPath "logs\qqq_phase5_paper_for_notion.csv" -Origin "LIVE" }

# 4) LIVE audit (NVDA + SPY + QQQ)
Run-Step -Name "Run Phase-5 LIVE audit" -Action { .\tools\Run-Phase5LiveAudit.ps1 }

Write-Host "`n[PHASE5] All micro sessions + CSV + LIVE audit completed successfully." -ForegroundColor Green
