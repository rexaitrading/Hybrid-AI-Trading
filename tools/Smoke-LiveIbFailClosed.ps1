[CmdletBinding()]
param(
  [string]$Symbol="NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$root = (Resolve-Path ".").Path
Set-Location $root

# UTF-8 console
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "[SMOKE] Python missing: $py" }

# Ensure local package import works
$env:PYTHONNOUSERSITE="1"
$env:PYTHONPATH = (Join-Path $root "src")
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"

# Force LIVE intent (but must fail-closed)
$env:HAT_IS_PAPER="0"

# Backup + force BlockG reject
$bg = Join-Path $root "logs\blockg_status_stub.json"
if (-not (Test-Path $bg)) { throw "[SMOKE] Missing: $bg" }

Copy-Item $bg "$bg.bak_smoke_live" -Force
try {
  $j = Get-Content $bg -Raw -Encoding utf8 | ConvertFrom-Json
  $j.nvda_blockg_ready = $false
  $j.spy_blockg_ready  = $false
  $j.qqq_blockg_ready  = $false
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText((Resolve-Path $bg).Path, ($j | ConvertTo-Json -Depth 12) + "`n", $utf8)

  # Run CLI; capture combined output
  $out = & $py -m hybrid_ai_trading.runners.ah_once --symbol $Symbol --qty 1 --side BUY --live 2>&1 | Out-String
  $rc = $LASTEXITCODE

  # Strict: must be a Block-G refusal, not usage/help, not module error, not env refusal
  if ($out -notmatch "BlockG|BLOCK-G|require_blockg_ready_for_live|blockg") {
    throw "[SMOKE] NOT BlockG failure. rc=$rc output=$out"
  }

  Write-Host "[SMOKE] ✅ BlockG fail-closed confirmed (rc=$rc)" -ForegroundColor Green
  exit 0
}
finally {
  Copy-Item "$bg.bak_smoke_live" $bg -Force
  Remove-Item "$bg.bak_smoke_live" -Force
  Remove-Item Env:\HAT_IS_PAPER -ErrorAction SilentlyContinue
}