param(
    [string] $Pattern      = "research\nvda_bplus_replay_trades*.jsonl",
    [double] $MinGateScore = 0.04
)

$ErrorActionPreference = "Stop"

Set-Location "C:\Users\rhcy9\OneDrive\文件\HybridAITrading"

Write-Host "=== NVDA B+ Gate + Eval (ALL) ==="
Write-Host "Pattern:      $Pattern"
Write-Host "MinGateScore: $MinGateScore"

$files = Get-ChildItem -Path $Pattern -File

if (-not $files) {
    Write-Host "[INFO] No files matched pattern: $Pattern"
    return
}

foreach ($f in $files) {
    $relPath = Join-Path "research" $f.Name
    Write-Host ""
    Write-Host "==== File: $relPath ===="

    .\tools\Run-NvdaBplusGateEval.ps1 `
        -InputJsonl $relPath `
        -MinGateScore $MinGateScore
}

Write-Host "`n=== NVDA B+ Gate + Eval (ALL) done ==="
