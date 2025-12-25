[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$expected = Join-Path $repoRoot ".venv\Scripts\python.exe"

$actual = powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $toolsDir "python.ps1") -c "import sys; print(sys.executable)"
$actual = ($actual | Out-String).Trim()

if($actual -ne $expected){
  Write-Host "REPO_PYTHON_OK=0 :: expected=$expected actual=$actual" -ForegroundColor Red
  exit 2
}

Write-Host "REPO_PYTHON_OK=1 :: $actual" -ForegroundColor Green
exit 0
