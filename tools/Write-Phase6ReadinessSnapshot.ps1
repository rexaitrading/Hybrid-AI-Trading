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

# Build a temp python runner (quoting-proof)
$tmp = Join-Path $env:TEMP ("hat_phase6_readiness_" + [guid]::NewGuid().ToString("N") + ".py")

$pyLines = @(
  'import json, os',
  'from pathlib import Path',
  'from hybrid_ai_trading.phase6.readiness_snapshot import write_readiness_snapshot as w',
  '',
  'cfg_json = os.environ.get("HAT_PORTFOLIO_HALT_CFG_JSON", "") or "{}"',
  'try:',
  '    cfg = json.loads(cfg_json) if isinstance(cfg_json, str) else {}',
  'except Exception:',
  '    cfg = {}',
  '',
  'repo_root = Path(__file__).resolve().parents[3]',
  'mp = repo_root / "logs" / "phase6_portfolio_metrics.json"',
  'metrics = {}',
  'try:',
  '    if mp.exists():',
  '        metrics = json.loads(mp.read_text(encoding="utf-8-sig"))',
  '        if not isinstance(metrics, dict):',
  '            metrics = {}',
  'except Exception:',
  '    metrics = {}',
  '',
  'p = w(portfolio_metrics=metrics, portfolio_cfg=cfg)',
  'print(str(p))'
)

$pyCode = ($pyLines -join "`n") + "`n"
[System.IO.File]::WriteAllText($tmp, $pyCode, (New-Object System.Text.UTF8Encoding($false)))

try {
  & $py $tmp
  exit $LASTEXITCODE
}
finally {
  Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}
