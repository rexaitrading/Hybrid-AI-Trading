# Activates venv then self-heals pip if missing
param()
. "$PSScriptRoot\..\.\.venv\Scripts\Activate.ps1"
try { pip -V | Out-Null } catch {
  Write-Host "⚙️  Re-installing pip..." -ForegroundColor Yellow
  & "$env:VIRTUAL_ENV\Scripts\python.exe" -m ensurepip --upgrade
}
