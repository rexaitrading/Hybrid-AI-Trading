[CmdletBinding()]
param()

Write-Host "[OPS] Block-G checks must run as CHILD process (never directly)." -ForegroundColor Cyan
Write-Host "Run:" -ForegroundColor Cyan
Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Invoke-BlockGReady.ps1 -Symbol ALL -Build" -ForegroundColor Yellow
Write-Host "Or:" -ForegroundColor Cyan
Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Check-BlockGReady-Wrapper.ps1 -Symbol NVDA" -ForegroundColor Yellow
return 0