[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)]
  [string]$AsOfDate = ""
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

# 1) Generate base paper_trades.jsonl (current generator)
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Write-NvdaPaperTradesStub.ps1 -Count 360
if ($LASTEXITCODE -ne 0) { throw "Write-NvdaPaperTradesStub.ps1 failed exit=$LASTEXITCODE" }
if (Test-Path .\tools\Write-SpyQqqPaperTradesStub.ps1) {
  if ([string]::IsNullOrWhiteSpace($AsOfDate)) {
    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Write-SpyQqqPaperTradesStub.ps1
  } else {
    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Write-SpyQqqPaperTradesStub.ps1 -AsOfDate $AsOfDate
  }

  $code2 = $(if (Get-Variable -Name LASTEXITCODE -ErrorAction SilentlyContinue) { $LASTEXITCODE } else { 0 })
  if ($code2 -ne 0) { throw "Write-SpyQqqPaperTradesStub.ps1 failed exit=$code2" }
} else {
  Write-Host "[PAPER-TRADES] WARN: missing tools\Write-SpyQqqPaperTradesStub.ps1 -> skip SPY/QQQ stubs (fail-closed)." -ForegroundColor Yellow
}
if ($LASTEXITCODE -ne 0) { throw "Write-NvdaPaperTradesStub.ps1 failed exit=$LASTEXITCODE" }

# 2) Normalize to today (in-place safe)
if ([string]::IsNullOrWhiteSpace($AsOfDate)) {
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Normalize-PaperTradesToday.ps1
} else {
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Normalize-PaperTradesToday.ps1 -AsOfDate $AsOfDate
}
if ($LASTEXITCODE -ne 0) { throw "Normalize-PaperTradesToday.ps1 failed exit=$LASTEXITCODE" }

# 3) Visibility
$paper = Join-Path $repoRoot "logs\paper_trades.jsonl"
Write-Host ("[PAPER-TRADES] READY: {0}" -f $paper) -ForegroundColor Green
Get-Content $paper -TotalCount 3
exit 0

