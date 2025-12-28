[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $py)){ $py = "python" }

& $py -c "from hybrid_ai_trading.phase6.readiness_snapshot import write_readiness_snapshot as w; p=w(); print(str(p))"
exit $LASTEXITCODE
