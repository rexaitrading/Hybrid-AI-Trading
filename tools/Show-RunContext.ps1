[CmdletBinding()]
param(
  [ValidateSet("premarket","paper","live","notion")]
  [string]$Mode = "paper",
  [string]$Symbol = "",
  [string]$Day = $(Get-Date -Format "yyyy-MM-dd")
)

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$env:PYTHONPATH = Join-Path $repoRoot "src"
$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Python not found: $py" }

$env:HAT_RUN_MODE = $Mode
if ($Symbol) { $env:HAT_SYMBOL = $Symbol } else { Remove-Item Env:\HAT_SYMBOL -ErrorAction SilentlyContinue }
$env:HAT_TRADING_DATE = $Day

& $py -c "from hybrid_ai_trading.runtime.run_context_builder import load_run_context; print(load_run_context())"
