[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA"
),
  [ValidateSet("ALL_STRICT","SYMBOL_ONLY","BUILD_ONLY")]
  [string]$Mode = "BUILD_ONLY"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

# Always rebuild the contract first (single producer)
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Build-BlockGStatusStub.ps1") | Out-Host
if ($LASTEXITCODE -ne 0) {
  $code = $LASTEXITCODE
  $global:LASTEXITCODE = $code
  return $code
}

$checker = Join-Path $repoRoot "tools\Check-BlockGReady.ps1"
if(-not (Test-Path -LiteralPath $checker)){ throw "Missing: $checker" }

if ($Symbol -eq "ALL") {
  $codes = @{}
  foreach ($sym in @("NVDA","SPY","QQQ")) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $checker -Symbol $sym -Mode $Mode
    $codes[$sym] = $LASTEXITCODE
  }

  # Fail-closed: if any symbol is non-zero, return 2 (contract fail)
  if (@($codes.Values | Where-Object { $_ -ne 0 }).Count -gt 0) {
    Write-Host ("BLOCK-G: NOT READY some symbols => " + ($codes.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" } -join ", ")) -ForegroundColor Yellow
    $global:LASTEXITCODE = 2
    return 2
  }

  Write-Host "BLOCK-G: READY for ALL symbols (NVDA, SPY, QQQ)." -ForegroundColor Green
  $global:LASTEXITCODE = 0
  return 0
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $checker -Symbol $sym -Mode $Modebol -Mode $Mode
$code = $LASTEXITCODE
$global:LASTEXITCODE = $code
return $code
