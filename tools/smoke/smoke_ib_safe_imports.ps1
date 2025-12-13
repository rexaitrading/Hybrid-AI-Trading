[CmdletBinding()]
param()

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent (Split-Path -Parent $toolsDir)
Set-Location $repoRoot

$env:PYTHONPATH = Join-Path $repoRoot "src"
$py = ".\.venv\Scripts\python.exe"

& $py -c "from hybrid_ai_trading.broker.ib_safe import retry, connect_ib, account_snapshot, cancel_all_open, force_refresh_positions, marketable_limit, map_ib_error; print('IMPORTS_OK')"