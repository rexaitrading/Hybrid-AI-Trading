[CmdletBinding()]
param(
  [Parameter(ValueFromRemainingArguments=$true)]
  [string[]]$Args
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

# Deterministic repo root (Unicode-safe)
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

# Force THIS repo imports (never C:\Dev\HybridAITrading)
$env:PYTHONPATH = (Join-Path $repoRoot "src")

# Force UTF-8 for any python subprocess (prevents cp1252 UnicodeEncodeError on non-ASCII paths)
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

# Force pytest temp to repo-writable path (prevents WinError 5 cleanup)
$tmpBase = Join-Path $repoRoot "logs\_pytest_tmp"
New-Item -ItemType Directory -Force -Path $tmpBase | Out-Null
$env:TEMP = (Resolve-Path $tmpBase).Path
$env:TMP  = (Resolve-Path $tmpBase).Path

# Console UTF-8 (prevents mojibake in logs)
chcp 65001 | Out-Null

# --- ENV CLEAN (tests must target default logs/) ---
Remove-Item Env:HAT_LOGS_DIR -ErrorAction SilentlyContinue
Remove-Item Env:HAT_BLOCKG_STATUS_PATH -ErrorAction SilentlyContinue
Remove-Item Env:HAT_BLOCKG_BUILT_ONCE -ErrorAction SilentlyContinue
Remove-Item Env:HAT_BLOCKG_QUIET -ErrorAction SilentlyContinue
# -----------------------------------------------

# Use UTF-8-safe python wrapper (prevents cp1252 UnicodeEncodeError)
$pywrap = Join-Path $toolsDir "python.ps1"
if(-not (Test-Path -LiteralPath $pywrap)){ throw "Missing python wrapper: $pywrap" }

# Repo-local basetemp (avoids pytest-of-* lock spam)
$tmp = Join-Path (Join-Path $repoRoot "logs") "_pytest_tmp"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null

# Prove sys.path is clean (UTF-8 safe; avoids cp1252 crash on non-ASCII PWD)
& $pywrap -c "import sys,os; print('PY=',sys.executable); print('PWD=',os.getcwd()); print('BAD_CDEV=', any(p.lower().startswith('c:\\dev\\hybridaitrading') for p in sys.path));"

# Run pytest
& $pywrap -m pytest --basetemp "$tmp" @Args
$global:LASTEXITCODE = $LASTEXITCODE
return
