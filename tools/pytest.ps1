[CmdletBinding()]
param(
  [Parameter(ValueFromRemainingArguments=$true)]
  [string[]]$Args
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $py)){ throw "Missing venv python: $py" }

# Force THIS repo imports (never C:\Dev\HybridAITrading)
$env:PYTHONPATH = (Join-Path $repoRoot "src")

# Force pytest temp to repo-writable path (prevents WinError 5 cleanup)
$tmpBase = Join-Path $repoRoot "logs\_pytest_tmp"
New-Item -ItemType Directory -Force -Path $tmpBase | Out-Null
$env:TEMP = (Resolve-Path $tmpBase).Path
$env:TMP  = (Resolve-Path $tmpBase).Path

chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

# --- ENV CLEAN (tests must target default logs/) ---
Remove-Item Env:HAT_LOGS_DIR -ErrorAction SilentlyContinue
Remove-Item Env:HAT_BLOCKG_STATUS_PATH -ErrorAction SilentlyContinue
Remove-Item Env:HAT_BLOCKG_BUILT_ONCE -ErrorAction SilentlyContinue
Remove-Item Env:HAT_BLOCKG_QUIET -ErrorAction SilentlyContinue
# -----------------------------------------------
$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $py)){ throw "Missing venv python: $py" }

# Hard-fix import root (prevents C:\Dev\HybridAITrading hijack)

# Repo-local basetemp (avoids pytest-of-* lock spam)
$tmp = Join-Path (Join-Path $repoRoot "logs") "_pytest_tmp"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null

# Prove sys.path is clean (optional but useful)
& $py -c "import sys,os; print('PY=',sys.executable); print('PWD=',os.getcwd()); print('BAD_CDEV=', any(p.lower().startswith('c:\\dev\\hybridaitrading') for p in sys.path));"

& $py -m pytest --basetemp "$tmp" @Args
$global:LASTEXITCODE = $LASTEXITCODE; return
