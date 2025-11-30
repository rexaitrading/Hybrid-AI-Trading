$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$logsDir   = Join-Path $repoRoot "logs"
$notionUrl = "https://www.notion.so/2970bf31ef1580a6983ecf2c836cf97c?v=2b80bf31ef15805d8474000c1dcd5507"

Write-Host "`n[OPEN] Opening logs folder (CSV location)..." -ForegroundColor Cyan
Start-Process $logsDir

Write-Host "[OPEN] Opening Notion Trading Journal in browser..." -ForegroundColor Cyan
Start-Process $notionUrl

Write-Host "[OPEN] Now you can use 'Merge with CSV' in Notion to import:" -ForegroundColor Yellow
Write-Host "  - nvda_phase5_paper_for_notion.csv" -ForegroundColor Yellow
Write-Host "  - spy_phase5_paper_for_notion.csv"  -ForegroundColor Yellow
Write-Host "  - qqq_phase5_paper_for_notion.csv"  -ForegroundColor Yellow
