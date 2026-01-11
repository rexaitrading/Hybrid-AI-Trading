[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol="NVDA",

  [switch]$RunCrypto
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
chcp 65001 | Out-Null

$repoRoot = "C:\HATJ\HybridAITrading"
Set-Location -LiteralPath $repoRoot
$env:HAT_REPO_ROOT = $repoRoot

Write-Host "[WEEKEND] Starting weekend ops (closed-day equities; optional crypto)" -ForegroundColor Yellow
Write-Host ("[WEEKEND] Date=" + (Get-Date).ToString("o")) -ForegroundColor DarkGray

# Closed-day: run master in HOLD; Block-G exit=10 is now allowed by patched RunTool()
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Master-Launch-Phase1to7.ps1 -Symbol $Symbol -Hold

# OPTIONAL: crypto runner (only if you already have one)
if($RunCrypto){
  $cand = @(
    ".\tools\Run-CryptoWeekend.ps1",
    ".\tools\Run-CryptoPaperOps.ps1",
    ".\tools\Run-CryptoOps.ps1"
  ) | Where-Object { Test-Path -LiteralPath (Join-Path $repoRoot $_) } | Select-Object -First 1

  if($cand){
    Write-Host ("[WEEKEND] Running crypto runner => " + $cand) -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File $cand *>&1 | Out-Host
  } else {
    Write-Host "[WEEKEND] RunCrypto requested, but no crypto runner script found (expected tools\Run-Crypto*.ps1)." -ForegroundColor Yellow
  }
}

Write-Host "[WEEKEND] Done." -ForegroundColor Green
exit 0
