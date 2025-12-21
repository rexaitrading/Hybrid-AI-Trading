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
  $args = @(
    "-m","hybrid_ai_trading.runners.ah_once",
    "--symbol",$Symbol,
    "--force","BUY",
    "--qty","1",
    "--order-type","MKT"
  )
  $oldEap = $ErrorActionPreference
  try {
    # We EXPECT failure here (BlockGNotReady). Do not terminate the script.
    $ErrorActionPreference = "Continue"
    $out = & $py @args 2>&1 | Out-String
  }
  finally {
    $ErrorActionPreference = $oldEap
  }
  $rc = $LASTEXITCODE

  # SMOKE_USAGE_GUARD: never treat argparse usage/help as a BlockG success
  if ($out -match "usage:\s+ah_once" -or $out -match "the following arguments are required") {
    throw "[SMOKE] ah_once CLI usage/arg mismatch. output=$out"
  }
    # Strict: must be a Block-G refusal.
  # Accept either plain message OR Python traceback containing BlockGNotReady/BLOCK-G.
  $is_blockg = ($out -match "BlockGNotReady" -or $out -match "BLOCK-G:" -or $out -match "nvda_blockg_ready=false" -or $out -match "require_blockg_ready_for_live")

  if (-not $is_blockg) {
    # If we got any traceback but it's NOT Block-G, that's a real failure.
    if ($out -match "Traceback \(most recent call last\):") {
      throw "[SMOKE] Traceback not caused by Block-G. rc=$rc output=$out"
    }
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