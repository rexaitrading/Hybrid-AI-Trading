# ===========================================
# Hybrid AI Quant Pro â€“ Local CI Debug Script
# ===========================================
# Runs pytest, coverage, and linting exactly like CI.
# Shows exit codes so you know *why* it turned red.

Write-Host "ðŸš€ Running local CI checks..." -ForegroundColor Cyan

# 1. Clean old caches
Remove-Item .coverage -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force htmlcov -ErrorAction SilentlyContinue

# 2. Run pytest with coverage
Write-Host "`nðŸ§ª Running pytest with coverage..." -ForegroundColor Yellow
pytest -v `
  --maxfail=1 --disable-warnings `
  --cov=src/hybrid_ai_trading `
  --cov-branch `
  --cov-report=term-missing `
  --cov-report=html `
  --cov-fail-under=100

$lastExit = $LASTEXITCODE
if ($lastExit -ne 0) {
    Write-Host "âŒ Pytest failed with exit code $lastExit" -ForegroundColor Red
} else {
    Write-Host "âœ… Pytest passed" -ForegroundColor Green
}

# 3. Run flake8 linting
Write-Host "`nðŸ”Ž Running flake8 lint checks..." -ForegroundColor Yellow
flake8 src tests
$lastLint = $LASTEXITCODE
if ($lastLint -ne 0) {
    Write-Host "âŒ Flake8 lint errors detected" -ForegroundColor Red
} else {
    Write-Host "âœ… Flake8 passed" -ForegroundColor Green
}

# 4. Run black formatting check
Write-Host "`nðŸŽ¨ Running black formatting check..." -ForegroundColor Yellow
black --check src tests
$lastBlack = $LASTEXITCODE
if ($lastBlack -ne 0) {
    Write-Host "âŒ Black formatting issues detected" -ForegroundColor Red
} else {
    Write-Host "âœ… Black formatting passed" -ForegroundColor Green
}

# 5. Summary
Write-Host "`nðŸ“Š CI Check Summary" -ForegroundColor Cyan
Write-Host "pytest exit code: $lastExit"
Write-Host "flake8 exit code: $lastLint"
Write-Host "black exit code: $lastBlack"

if ($lastExit -eq 0 -and $lastLint -eq 0 -and $lastBlack -eq 0) {
    Write-Host "`nðŸŽ‰ All checks passed locally â€“ should be green in CI!" -ForegroundColor Green
} else {
    Write-Host "`nâš ï¸ Some checks failed â€“ see logs above." -ForegroundColor Red
}
