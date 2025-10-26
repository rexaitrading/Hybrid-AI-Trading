# Activates venv, forces UTF-8, and self-heals pip if missing
param()

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$env:PYTHONIOENCODING = 'utf-8'
try { chcp 65001 | Out-Null } catch {}

# Call the signed default activate script
. "$PSScriptRoot\..\.\.venv\Scripts\Activate.ps1"

# Verify pip using python -m pip to avoid encoding issues
try {
    & "$env:VIRTUAL_ENV\Scripts\python.exe" -m pip --version | Out-Null
} catch {
    Write-Host 'Re-installing pip...' -ForegroundColor Yellow
    & "$env:VIRTUAL_ENV\Scripts\python.exe" -m ensurepip --upgrade
}