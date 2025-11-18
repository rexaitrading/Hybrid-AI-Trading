param(
    [string] $InputJsonl      = "research\nvda_bplus_replay_trades.jsonl",
    [double] $MinGateScore    = 0.04
)

$ErrorActionPreference = "Stop"

Set-Location "C:\Users\rhcy9\OneDrive\文件\HybridAITrading"
.\.venv\Scripts\activate.ps1
$py = ".\.venv\Scripts\python.exe"

Write-Host "=== NVDA B+ Gate + Notion ==="
Write-Host "Input:        $InputJsonl"
Write-Host "MinGateScore: $MinGateScore"

# 1) Apply gate
& $py tools\nvda_bplus_apply_gate.py `
    --input $InputJsonl `
    --min-gate-score $MinGateScore

# Derive gated file path (same as gate/eval pipeline)
$stem      = [System.IO.Path]::GetFileNameWithoutExtension($InputJsonl)
$gatedName = ("{0}_g{1:N2}.jsonl" -f $stem, $MinGateScore)
$gatedName = $gatedName -replace ",", "."
$gatedPath = Join-Path "research" $gatedName

Write-Host "[INFO] Using gated file for Notion: $gatedPath"

# 2) Enrich gated trades for Notion
$enrichedName = ("{0}_enriched.jsonl" -f $gatedName.Substring(0, $gatedName.Length - 6))  # strip .jsonl, add _enriched.jsonl
$enrichedPath = Join-Path "research" $enrichedName

Write-Host "[INFO] Enriched output:        $enrichedPath"

& $py tools\nvda_bplus_enrich_replay_jsonl.py `
    --input $gatedPath `
    --output $enrichedPath

# 3) Push enriched, gated trades to Notion
Write-Host "[INFO] Pushing to Notion using: $enrichedPath"

& $py tools\nvda_bplus_push_to_notion.py `
    --jsonl $enrichedPath

Write-Host "=== NVDA B+ Gate + Notion done ==="
