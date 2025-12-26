[CmdletBinding()]
param(
  [int]$Tail = 60,
  [string]$Model = "gpt-4.1-mini"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

# Load local vault env first (safe; no printing)
$loader = Join-Path $repoRoot "tools\Load-HatSecrets.ps1"
if(Test-Path $loader){ & $loader | Out-Null }

$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $py)){ throw "Missing venv python: $py" }

$env:PYTHONPATH = $repoRoot
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$script = Join-Path $repoRoot "scripts\llm_intel_features.py"
if(-not (Test-Path $script)){ throw "Missing: $script" }

& $py $script --intelDir "src/.intel" --tail $Tail --model $Model
exit $LASTEXITCODE