[CmdletBinding()]
param(
  [Parameter()][string]$Mode = "premarket",
  [Parameter()][string]$Symbol = "NVDA"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# --- UTF-8 console for child Python ---
try { [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false) } catch {}
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONIOENCODING = "utf-8"
# -------------------------------------

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$py = Join-Path $repoRoot ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Python not found at: $py" }

$script = Join-Path $repoRoot "tools\show_run_context.py"
if (-not (Test-Path $script)) { throw "Missing: $script" }

& $py $script -Mode $Mode -Symbol $Symbol
