[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath

# FAIL-CLOSED: no tool script may invoke raw `python` directly.
# Only allow tools/python.ps1 as the canonical entrypoint.
$pattern = '^\s*(?!#)\s*python(\.exe)?\s+'

$hits = Select-String -Path (Join-Path $toolsDir "*.ps1") -Pattern $pattern -AllMatches -ErrorAction SilentlyContinue

if($hits){
  Write-Host "RAW_PYTHON_IN_TOOLS=1" -ForegroundColor Red
  $hits | Select-Object Path,LineNumber,Line | Format-Table -AutoSize | Out-Host
  Write-Host "Fix: replace raw python calls with tools/python.ps1 wrapper." -ForegroundColor Yellow
  exit 2
}

Write-Host "RAW_PYTHON_IN_TOOLS=0" -ForegroundColor Green
exit 0
