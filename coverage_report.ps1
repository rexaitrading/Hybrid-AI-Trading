# coverage_report.ps1
# --------------------------------------------------------
# Run all tests with coverage and generate reports:
#  1. Terminal summary (per-file coverage with missing lines)
#  2. Text summary saved to coverage_summary.txt
#  3. HTML report saved to htmlcov/index.html
# --------------------------------------------------------

Write-Host "🧪 Running tests with coverage..." -ForegroundColor Cyan

# Clean old coverage
if (Test-Path .coverage) { Remove-Item .coverage -Force }
if (Test-Path coverage_summary.txt) { Remove-Item coverage_summary.txt -Force }
if (Test-Path htmlcov) { Remove-Item htmlcov -Recurse -Force }

# Run pytest with coverage
pytest tests -vv --cache-clear `
  --cov=src/hybrid_ai_trading `
  --cov-branch `
  --cov-report=term-missing `
  --cov-report=html `
  --disable-warnings `
  | Tee-Object -FilePath coverage_summary.txt

Write-Host "`n✅ Coverage reports generated:" -ForegroundColor Green
Write-Host "   • coverage_summary.txt   (plain text report)"
Write-Host "   • htmlcov/index.html     (open in browser for full UI)" -ForegroundColor Yellow
