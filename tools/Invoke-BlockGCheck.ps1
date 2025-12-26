[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

# Always rebuild the contract first (single producer)
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Build-BlockGStatusStub.ps1") | Out-Host
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$checker = Join-Path $repoRoot "tools\Check-BlockGReady.ps1"

if ($Symbol -eq "ALL") {
  $codes = @{}
  foreach ($sym in @("NVDA","SPY","QQQ")) {
    powershell -NoProfile -ExecutionPolicy Bypass -File $checker -Symbol $sym
    $codes[$sym] = $LASTEXITCODE
  }

  # Fail-closed: if any symbol is non-zero, exit 2 (contract fail)
  if (@($codes.Values | Where-Object { $_ -ne 0 }).Count -gt 0) {
    Write-Host ("BLOCK-G: NOT READY some symbols => " + ($codes.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" } -join ", ")) -ForegroundColor Yellow
    exit 2
  }

  Write-Host "BLOCK-G: READY for ALL symbols (NVDA, SPY, QQQ)." -ForegroundColor Green
  exit 0
}

powershell -NoProfile -ExecutionPolicy Bypass -File $checker -Symbol $Symbol
exit $LASTEXITCODE