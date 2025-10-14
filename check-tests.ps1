# ===========================================
# Hybrid AI Quant Pro – Local CI Debug Script
# ===========================================
# Runs pytest, coverage, and linting exactly like CI.
# Shows exit codes so you know *why* it turned red.

Write-Host "🚀 Running local CI checks..." -ForegroundColor Cyan

# 1. Clean old caches
Remove-Item .coverage -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force htmlcov -ErrorAction SilentlyContinue

# 2. Run pytest with coverage
Write-Host "`n🧪 Running pytest with coverage..." -ForegroundColor Yellow
pytest -v `
  --maxfail=1 --disable-warnings `
  --cov=src/hybrid_ai_trading `
  --cov-branch `
  --cov-report=term-missing `
  --cov-report=html `
  --cov-fail-under=100

$lastExit = $LASTEXITCODE
if ($lastExit -ne 0) {
    Write-Host "❌ Pytest failed with exit code $lastExit" -ForegroundColor Red
} else {
    Write-Host "✅ Pytest passed" -ForegroundColor Green
}

# 3. Run flake8 linting
Write-Host "`n🔎 Running flake8 lint checks..." -ForegroundColor Yellow
flake8 src tests
$lastLint = $LASTEXITCODE
if ($lastLint -ne 0) {
    Write-Host "❌ Flake8 lint errors detected" -ForegroundColor Red
} else {
    Write-Host "✅ Flake8 passed" -ForegroundColor Green
}

# 4. Run black formatting check
Write-Host "`n🎨 Running black formatting check..." -ForegroundColor Yellow
black --check src tests
$lastBlack = $LASTEXITCODE
if ($lastBlack -ne 0) {
    Write-Host "❌ Black formatting issues detected" -ForegroundColor Red
} else {
    Write-Host "✅ Black formatting passed" -ForegroundColor Green
}

# 5. Summary
Write-Host "`n📊 CI Check Summary" -ForegroundColor Cyan
Write-Host "pytest exit code: $lastExit"
Write-Host "flake8 exit code: $lastLint"
Write-Host "black exit code: $lastBlack"

if ($lastExit -eq 0 -and $lastLint -eq 0 -and $lastBlack -eq 0) {
    Write-Host "`n🎉 All checks passed locally – should be green in CI!" -ForegroundColor Green
} else {
    Write-Host "`n⚠️ Some checks failed – see logs above." -ForegroundColor Red
}
