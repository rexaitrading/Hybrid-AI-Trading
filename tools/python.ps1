[CmdletBinding()]
param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $py)) { throw "Missing venv python: $py" }

# Force UTF-8 output (prevents pip/rich cp1252 crashes)
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

& $py @Args
exit $LASTEXITCODE
