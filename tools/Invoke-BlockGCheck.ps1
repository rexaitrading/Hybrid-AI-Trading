[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA",

  [ValidateSet("ALL_STRICT","SYMBOL_ONLY","BUILD_ONLY")]
  [string]$Mode = "BUILD_ONLY"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

# 0) Build contract first (single producer of blockg_status_stub.json)
$builder = Join-Path $repoRoot "tools\Build-BlockGStatusStub.ps1"
if(-not (Test-Path -LiteralPath $builder)){ throw "Missing builder: $builder" }

& powershell -NoProfile -ExecutionPolicy Bypass -File $builder -Symbol $Symbol *>&1 | Out-Host
if ($LASTEXITCODE -ne 0) {
  $code = $LASTEXITCODE
  $global:LASTEXITCODE = $code
  return $code
}

# 1) Contract-only checker
$checker = Join-Path $repoRoot "tools\Check-BlockGReady.ps1"
if(-not (Test-Path -LiteralPath $checker)){ throw "Missing checker: $checker" }

if ($Symbol -eq "ALL") {
  $codes = @{}
  foreach ($sym in @("NVDA","SPY","QQQ")) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $checker -Symbol $sym -Mode $Mode *>&1 | Out-Host
    $codes[$sym] = $LASTEXITCODE
  }

  # Fail-closed: if any symbol is non-zero, return 2
  if (@($codes.Values | Where-Object { $_ -ne 0 }).Count -gt 0) {
    Write-Host ("[BLOCKG] NOT READY some symbols => " + ($codes.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" } -join ", ")) -ForegroundColor Yellow
    $global:LASTEXITCODE = 2
    return 2
  }

  Write-Host "[BLOCKG] READY for ALL symbols (NVDA, SPY, QQQ)." -ForegroundColor Green
  $global:LASTEXITCODE = 0
  return 0
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $checker -Symbol $Symbol -Mode $Mode *>&1 | Out-Host
$code = $LASTEXITCODE
$global:LASTEXITCODE = $code
return $code
