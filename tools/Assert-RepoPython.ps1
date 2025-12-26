[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$expected = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $expected)){
  Write-Host "REPO_PYTHON_OK=0 :: missing expected=$expected" -ForegroundColor Red
  exit 2
}

function Sha256File([string]$path){
  (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
}

$expectedHash = Sha256File $expected

# Ask the canonical wrapper for two facts:
#  1) sys.executable (log only)
#  2) SHA256 of sys.executable file (authoritative identity check)
$pywrap = Join-Path $toolsDir "python.ps1"

$exe = powershell -NoProfile -ExecutionPolicy Bypass -File $pywrap -c "import sys; print(sys.executable)"
$exe = ($exe | Out-String).Trim()

$actualHash = powershell -NoProfile -ExecutionPolicy Bypass -File $pywrap -c @"
import hashlib, sys
p = sys.executable
h = hashlib.sha256()
with open(p, 'rb') as f:
    for chunk in iter(lambda: f.read(1024*1024), b''):
        h.update(chunk)
print(h.hexdigest())
"@
$actualHash = ($actualHash | Out-String).Trim().ToLowerInvariant()

if($expectedHash -eq $actualHash){
  Write-Host "REPO_PYTHON_OK=1 :: exe=$exe sha256=$actualHash" -ForegroundColor Green
  exit 0
}

Write-Host "REPO_PYTHON_OK=0 :: exe=$exe expected_sha256=$expectedHash actual_sha256=$actualHash" -ForegroundColor Red
exit 2
