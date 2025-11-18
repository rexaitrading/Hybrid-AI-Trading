param(
    [string] $InputJsonl      = "research\nvda_bplus_replay_trades.jsonl",
    [double] $MinGateScore    = 0.04
)

$ErrorActionPreference = "Stop"

# 1) Ensure repo root
Set-Location "C:\Users\rhcy9\OneDrive\文件\HybridAITrading"

# 2) Activate venv
.\.venv\Scripts\activate.ps1

$py = ".\.venv\Scripts\python.exe"

Write-Host "=== NVDA B+ Gate + Eval ==="
Write-Host "Input:        $InputJsonl"
Write-Host "MinGateScore: $MinGateScore"

# 3) Apply gate to replay JSONL
Write-Host "`n[STEP] Applying gate..."
& $py tools\nvda_bplus_apply_gate.py `
    --input $InputJsonl `
    --min-gate-score $MinGateScore

# Derive gated file name (repo-root + research)
$stem     = [System.IO.Path]::GetFileNameWithoutExtension($InputJsonl)
$gatedName = ("{0}_g{1:N2}.jsonl" -f $stem, $MinGateScore)
$gatedName = $gatedName -replace ",", "."
$gatedPath = Join-Path "research" $gatedName

Write-Host "[INFO] Gated file (expected): $gatedPath"

# 4) Eval raw
Write-Host "`n[STEP] Eval RAW..."
& $py tools\nvda_bplus_eval.py `
    --input $InputJsonl `
    --label "raw"

# 5) Eval gated
Write-Host "`n[STEP] Eval GATED..."
& $py tools\nvda_bplus_eval.py `
    --input $gatedPath `
    --label ("g{0:N2}" -f $MinGateScore)

# 6) Sweep on gated file for cross-check (optional but useful)
Write-Host "`n[STEP] Sweep on GATED..."
& $py tools\nvda_bplus_threshold_sweep.py `
    --jsonl $gatedPath `
    --limit 0 `
    --start 0.00 `
    --stop 0.12 `
    --step 0.01

Write-Host "`n=== NVDA B+ Gate + Eval done ==="

