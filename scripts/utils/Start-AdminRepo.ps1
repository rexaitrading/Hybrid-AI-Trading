param()
# Relaunch elevated if not admin
$wi = [Security.Principal.WindowsIdentity]::GetCurrent()
$pr = New-Object Security.Principal.WindowsPrincipal($wi)
if (-not $pr.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  Start-Process PowerShell -Verb RunAs -ArgumentList '-NoProfile','-NoExit','-Command','Set-ExecutionPolicy Bypass -Scope Process -Force; Set-Location C:\Dev\HybridAITrading; [Environment]::CurrentDirectory=(Get-Location).Path; Write-Host \"Admin shell at $(Get-Location)\" -ForegroundColor Green'
  exit
}
Set-Location C:\Dev\HybridAITrading
[Environment]::CurrentDirectory=(Get-Location).Path
Write-Host "Admin shell at $(Get-Location)" -ForegroundColor Green
