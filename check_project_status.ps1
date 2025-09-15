# ================================
# HybridAITrading Project Status Check
# ================================

Write-Host "=== [1] Python Environment Info ===" -ForegroundColor Cyan
python --version
pip --version
pip list | Select-String "pytest|coverage|pandas|requests"

Write-Host "`n=== [2] Virtual Environment ===" -ForegroundColor Cyan
Write-Host "Active VENV: $env:VIRTUAL_ENV"
if (-Not $env:VIRTUAL_ENV) {
    Write-Host "⚠️ No virtual environment active!" -ForegroundColor Yellow
}

Write-Host "`n=== [3] Project Folder Structure (src + tests) ===" -ForegroundColor Cyan
Get-ChildItem -Recurse -Directory src\hybrid_ai_trading, tests |
    Select-Object FullName

Write-Host "`n=== [4] Key Python Files (signals & risk modules) ===" -ForegroundColor Cyan
Get-ChildItem src\hybrid_ai_trading\signals\*.py
Get-ChildItem src\hybrid_ai_trading\risk\*.py

Write-Host "`n=== [5] Run pytest smoke test ===" -ForegroundColor Cyan
$pytestResult = python -m pytest -q --maxfail=1 --disable-warnings
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️ pytest had issues" -ForegroundColor Yellow
}

Write-Host "`n=== [6] Coverage quick check (signals only) ===" -ForegroundColor Cyan
python -m pytest -q --disable-warnings `
    --cov=src/hybrid_ai_trading/signals `
    --cov-branch --cov-report=term-missing --maxfail=1

Write-Host "`n=== [7] Done ===" -ForegroundColor Cyan
