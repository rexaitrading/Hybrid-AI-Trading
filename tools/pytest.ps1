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

# Hard-fix import root (prevents C:\Dev\HybridAITrading hijack)
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
$env:PYTHONPATH = (Join-Path $repoRoot "src")

# Repo-local basetemp (avoids pytest-of-* lock spam)
$tmp = Join-Path (Join-Path $repoRoot "logs") "_pytest_tmp"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null

# Prove sys.path is clean (optional but useful)
& $py -c "import sys,os; print('PY=',sys.executable); print('PWD=',os.getcwd()); print('BAD_CDEV=', any(p.lower().startswith('c:\\dev\\hybridaitrading') for p in sys.path));"

& $py -m pytest --basetemp "$tmp" @Args
$global:LASTEXITCODE = $LASTEXITCODE; return
