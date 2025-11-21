[CmdletBinding()]
param(
    [string]$DateTag = (Get-Date -Format 'yyyyMMdd'),
    [string]$ReplayOutDir = 'replay_out'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptRoot = $PSScriptRoot
$repoRoot   = Split-Path -Parent $scriptRoot
Set-Location $repoRoot

Write-Host "=== Run-Phase5ResearchToNotion.ps1 ===" -ForegroundColor Cyan
Write-Host "Repo    : $repoRoot"
Write-Host "DateTag : $DateTag"
Write-Host ""

$py = '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
    throw "Python not found: $py"
}

$srcPath = Join-Path $repoRoot 'src'
$env:PYTHONPATH = $srcPath

# 1) Run the multi-symbol research pipeline (NVDA + SPY + QQQ)
Write-Host "[BLOCK] Phase5 Multi-Symbol Research (NVDA + SPY + QQQ)" -ForegroundColor Cyan
& .\tools\Run-Phase5MultiResearch.ps1 -DateTag $DateTag
if ($LASTEXITCODE -ne 0) {
    throw "Run-Phase5MultiResearch.ps1 failed (exit=$LASTEXITCODE)"
}

# 2) Push NVDA B+, SPY ORB, QQQ ORB to Notion
$nvdaEnriched = Join-Path $ReplayOutDir ("nvda_bplus_trades_{0}_enriched.jsonl" -f $DateTag)
$spyJson      = Join-Path $ReplayOutDir ("spy_orb_trades_{0}_orb5_tp2.5.jsonl" -f $DateTag)
$qqqJson      = Join-Path $ReplayOutDir ("qqq_orb_trades_{0}_orb5_tp2.5.jsonl" -f $DateTag)

Write-Host ""
Write-Host "NVDA enriched JSONL : $nvdaEnriched"
Write-Host "SPY ORB JSONL       : $spyJson"
Write-Host "QQQ ORB JSONL       : $qqqJson"
Write-Host ""

if (-not (Test-Path $nvdaEnriched)) {
    throw "NVDA enriched JSONL not found: $nvdaEnriched"
}
if (-not (Test-Path $spyJson)) {
    throw "SPY ORB JSONL not found: $spyJson"
}
if (-not (Test-Path $qqqJson)) {
    throw "QQQ ORB JSONL not found: $qqqJson"
}

Write-Host "[STEP 2a] Push NVDA B+ replay trades to Notion" -ForegroundColor Cyan
& $py tools\nvda_bplus_push_to_notion.py `
    --jsonl $nvdaEnriched
if ($LASTEXITCODE -ne 0) {
    throw "nvda_bplus_push_to_notion.py failed (exit=$LASTEXITCODE)"
}

Write-Host "[STEP 2b] Push SPY ORB replay trades to Notion" -ForegroundColor Cyan
& $py tools\spy_orb_push_to_notion.py `
    --jsonl $spyJson
if ($LASTEXITCODE -ne 0) {
    throw "spy_orb_push_to_notion.py failed (exit=$LASTEXITCODE)"
}

Write-Host "[STEP 2c] Push QQQ ORB replay trades to Notion" -ForegroundColor Cyan
& $py tools\qqq_orb_push_to_notion.py `
    --jsonl $qqqJson
if ($LASTEXITCODE -ne 0) {
    throw "qqq_orb_push_to_notion.py failed (exit=$LASTEXITCODE)"
}

Write-Host ""
Write-Host "[DONE] Run-Phase5ResearchToNotion.ps1 completed for DateTag=$DateTag" -ForegroundColor Green
Write-Host "NVDA enriched JSONL : $nvdaEnriched"
Write-Host "SPY ORB JSONL       : $spyJson"
Write-Host "QQQ ORB JSONL       : $qqqJson"