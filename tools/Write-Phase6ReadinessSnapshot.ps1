[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $py)){ $py = "python" }

# Read cfg from env (JSON). Default {}.
$cfgJson = ($env:HAT_PORTFOLIO_HALT_CFG_JSON + "")
if([string]::IsNullOrWhiteSpace($cfgJson)){ $cfgJson = "{}" }

# Write a temp python runner to avoid PS quoting issues.
$tmp = Join-Path $env:TEMP ("hat_phase6_readiness_" + [guid]::NewGuid().ToString("N") + ".py")
$pyCode = @"
import json, os
from hybrid_ai_trading.phase6.readiness_snapshot import write_readiness_snapshot as w

cfg_json = os.environ.get("HAT_PORTFOLIO_HALT_CFG_JSON", "") or "{}"
try:
    cfg = json.loads(cfg_json) if isinstance(cfg_json, str) else {}
except Exception:
    cfg = {}

p = w(portfolio_cfg=cfg)
print(str(p))
"@
[System.IO.File]::WriteAllText($tmp, $pyCode, (New-Object System.Text.UTF8Encoding($false)))

try {
  & $py $tmp
  exit $LASTEXITCODE
}
finally {
  Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}
