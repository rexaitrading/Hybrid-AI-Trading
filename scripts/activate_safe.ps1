# Activates venv, forces UTF-8, then self-heals pip if needed (no emoji, CP1252-safe)
param()

# Force UTF-8 for console and Python I/O
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$env:PYTHONIOENCODING = 'utf-8'
try { chcp 65001 | Out-Null } catch {}

# Activate signed venv script
. "$PSScriptRoot\..\.\.venv\Scripts\Activate.ps1"

# Verify pip using python -m pip to avoid shim issues and CP1252 path printing
try {
  & "$env:VIRTUAL_ENV\Scripts\python.exe" -m pip --version | Out-Null
} catch {
  Write-Host "Re-installing pip..." -ForegroundColor Yellow
  & "$env:VIRTUAL_ENV\Scripts\python.exe" -m ensurepip --upgrade
}
