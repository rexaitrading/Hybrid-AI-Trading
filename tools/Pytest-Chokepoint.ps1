[CmdletBinding()]
param(
  [Parameter(ValueFromRemainingArguments=$true)]
  [string[]]$Args
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $py)){ throw "Missing venv python: $py" }

# --- HARD ISOLATION (kills AppData\Local\Temp pytest-of-* lock loop) ---
$oldTMP  = $env:TMP
$oldTEMP = $env:TEMP
$oldADD  = $env:PYTEST_ADDOPTS
$oldDIS  = $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD

$tmpRoot = Join-Path $repoRoot "logs\_tmp"
$baseTmp = Join-Path $repoRoot "logs\_pytest_tmp"
New-Item -ItemType Directory -Force -Path $tmpRoot | Out-Null
New-Item -ItemType Directory -Force -Path $baseTmp | Out-Null

$env:TMP  = $tmpRoot
$env:TEMP = $tmpRoot
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
$env:PYTEST_ADDOPTS = ("--basetemp `"{0}`" " -f $baseTmp) + (($env:PYTEST_ADDOPTS + "") -replace '^\s+','')
# ----------------------------------------------------------------------

# Prevent C:\Dev hijack; ensure repo src is import root
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
$env:PYTHONPATH = (Join-Path $repoRoot "src")

try {
  & $py -m pytest @Args
  $global:LASTEXITCODE = $LASTEXITCODE
}
finally {
  $env:TMP  = $oldTMP
  $env:TEMP = $oldTEMP
  $env:PYTEST_ADDOPTS = $oldADD
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = $oldDIS
}
return
