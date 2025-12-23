Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ------------------------------------------------------------
# Check-Phase5Today.ps1 (NO PARAM BINDING)
# Reason: avoid PowerShell param-binding edge cases in CI/subprocess.
# We parse $args manually. This script delegates semantics to:
#   tools\Check-BlockGReady.ps1   (single semantic owner)
#
# Supported:
#   -Symbol NVDA|SPY|QQQ|ALL
#   -Build   (optional; only when caller wants builder to run)
# ------------------------------------------------------------

function Fail([string]$msg) {
  Write-Host "[PHASE5] ERROR: $msg" -ForegroundColor Yellow
  exit 1
}

# Defaults
$Symbol = "NVDA"
$Build  = $false

# Parse args manually (robust for subprocess.run list args)
for ($i=0; $i -lt $args.Count; $i++) {
  $a = [string]$args[$i]
  switch -Regex ($a) {
    '^-Symbol$' {
      if ($i + 1 -ge $args.Count) { Fail "Missing value after -Symbol" }
      $Symbol = [string]$args[$i+1]
      $i++
      continue
    }
    '^-Build$' {
      $Build = $true
      continue
    }
    default {
      # Also allow positional symbol: Check-Phase5Today.ps1 NVDA
      if ($i -eq 0 -and $a -and ($a -notmatch '^-')) {
        $Symbol = $a
        continue
      }
    }
  }
}
if ($null -eq $Symbol) { $Symbol = "" }
$Symbol = ([string]$Symbol).ToUpperInvariant().Trim()
if ($Symbol -notin @("NVDA","SPY","QQQ","ALL")) {
  Fail "invalid Symbol='$Symbol' (expected NVDA/SPY/QQQ/ALL)"
}

$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$checker  = Join-Path $toolsDir "Check-BlockGReady.ps1"
if (-not (Test-Path -LiteralPath $checker)) { Fail "missing Check-BlockGReady.ps1 at $checker" }

# Delegate only; propagate exit codes:
#   0 = ready
#   2 = contract not ready
#   1 = script error
if ($Symbol -eq "ALL") {
  foreach ($s in @("NVDA","SPY","QQQ")) {
    $argv = @("-Symbol", $s)
    if ($Build) { $argv += "-Build" }
    powershell -NoProfile -ExecutionPolicy Bypass -File $checker @argv | Out-Host
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  }
  Write-Host ("PHASE5: OK today ({0}) symbol=ALL" -f (Get-Date).ToString("yyyy-MM-dd")) -ForegroundColor Green
  exit 0
}

$argv = @("-Symbol", $Symbol)
if ($Build) { $argv += "-Build" }

powershell -NoProfile -ExecutionPolicy Bypass -File $checker @argv | Out-Host
exit $LASTEXITCODE
