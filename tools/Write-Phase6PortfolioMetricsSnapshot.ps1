[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

# Force UTF-8 python stdout
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $py)){ $py = "python" }

& $py -c "from hybrid_ai_trading.phase6.portfolio_metrics_snapshot import write_portfolio_metrics_snapshot as w; p=w(); print(str(p))"
exit $LASTEXITCODE
