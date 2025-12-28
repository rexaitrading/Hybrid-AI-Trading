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

# Read cfg from env (JSON). Default {}.
$cfgJson = ($env:HAT_PORTFOLIO_HALT_CFG_JSON + "")
if([string]::IsNullOrWhiteSpace($cfgJson)){ $cfgJson = "{}" }

# Load portfolio metrics snapshot deterministically (PowerShell side)
$metricsPath = Join-Path $repoRoot "logs\phase6_portfolio_metrics.json"
$metricsJson = "{}"
if(Test-Path -LiteralPath $metricsPath){
  $metricsJson = Get-Content -LiteralPath $metricsPath -Raw -Encoding utf8
  if([string]::IsNullOrWhiteSpace($metricsJson)){ $metricsJson = "{}" }
}

# Temp python runner + temp metrics file (no quoting traps)
$tmpPy = Join-Path $env:TEMP ("hat_phase6_readiness_" + [guid]::NewGuid().ToString("N") + ".py")
$tmpMetrics = Join-Path $env:TEMP ("hat_phase6_metrics_" + [guid]::NewGuid().ToString("N") + ".json")

# Write temp metrics (UTF-8 no BOM)
[System.IO.File]::WriteAllText($tmpMetrics, ($metricsJson -replace "`r`n","`n").TrimEnd() + "`n", (New-Object System.Text.UTF8Encoding($false)))

# Point python to this explicit metrics file
$env:HAT_PHASE6_PORTFOLIO_METRICS_PATH = $tmpMetrics

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
  'mp = os.environ.get("HAT_PHASE6_PORTFOLIO_METRICS_PATH", "") or ""',
  'metrics = {}',
  'try:',
  '    if mp:',
  '        p = Path(mp)',
  '        if p.exists():',
  '            metrics = json.loads(p.read_text(encoding="utf-8-sig"))',
  '            if not isinstance(metrics, dict):',
  '                metrics = {}',
  'except Exception:',
  '    metrics = {}',
  '',
  'p = w(portfolio_metrics=metrics, portfolio_cfg=cfg)',
  'print(str(p))'
)
$pyCode = ($pyLines -join "`n") + "`n"
[System.IO.File]::WriteAllText($tmpPy, $pyCode, (New-Object System.Text.UTF8Encoding($false)))

try {
  & $py $tmpPy
  exit $LASTEXITCODE
}
finally {
  Remove-Item -LiteralPath $tmpPy -Force -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath $tmpMetrics -Force -ErrorAction SilentlyContinue
  Remove-Item Env:\HAT_PHASE6_PORTFOLIO_METRICS_PATH -ErrorAction SilentlyContinue
}
