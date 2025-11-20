[CmdletBinding()]
param(
    # Optional: specific DateTag like 20250101; if omitted, will use the latest *_enriched.jsonl
    [string]$DateTag
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# This script lives in tools\, repo root is its parent
$scriptRoot = $PSScriptRoot
$repoRoot   = Split-Path -Parent $scriptRoot

Set-Location $repoRoot

# === Environment + paths ===
$py       = '.venv\Scripts\python.exe'
$pusher   = Join-Path $repoRoot 'tools\nvda_bplus_push_to_notion.py'
$replayOut = Join-Path $repoRoot 'replay_out'

# Notion data source id for Trading Journal (NVDA B+ GateScore view lives on top of this)
if (-not $env:NOTION_JOURNAL_DS -or [string]::IsNullOrWhiteSpace($env:NOTION_JOURNAL_DS)) {
    throw "NOTION_JOURNAL_DS environment variable is not set. Set it to your Trading Journal data_source_id."
}

if (-not (Test-Path $py)) {
    throw "Python not found: $py"
}
if (-not (Test-Path $pusher)) {
    throw "Notion push helper not found: $pusher"
}
if (-not (Test-Path $replayOut)) {
    throw "replay_out folder not found: $replayOut. Run Run-NvdaBplusReplay.ps1 first."
}

# === Resolve which enriched JSONL to use ===
$enrichedPath = $null

if ($DateTag) {
    # Explicit DateTag -> use nvda_bplus_trades_<DateTag>_enriched.jsonl
    $candidate = Join-Path $replayOut ("nvda_bplus_trades_{0}_enriched.jsonl" -f $DateTag)
    if (-not (Test-Path $candidate)) {
        throw "Enriched JSONL for DateTag '$DateTag' not found: $candidate. Make sure Run-NvdaBplusReplay.ps1 -DateTag $DateTag has been run."
    }
    $enrichedPath = $candidate
}
else {
    # No DateTag: pick the most recent *_enriched.jsonl
    $pattern = 'nvda_bplus_trades_*_enriched.jsonl'
    $files = Get-ChildItem -Path $replayOut -Filter $pattern -File |
             Sort-Object LastWriteTime -Descending
    if (-not $files -or $files.Count -eq 0) {
        throw "No enriched NVDA B+ replay files found under $replayOut with pattern $pattern. Run Run-NvdaBplusReplay.ps1 first."
    }
    $enrichedPath = $files[0].FullName
}

Write-Host "=== Update-NotionNvdaBplusReplay ===" -ForegroundColor Cyan
Write-Host "Repo root        : $repoRoot"
Write-Host "Replay_out       : $replayOut"
Write-Host "Enriched JSONL   : $enrichedPath"
Write-Host "NOTION_JOURNAL_DS: $($env:NOTION_JOURNAL_DS)"
Write-Host ""

# === Optional peek: show first 12 trades for sanity ===
try {
    $previewLines = Get-Content -LiteralPath $enrichedPath -TotalCount 2
    Write-Host "[PREVIEW] First trade line(s):" -ForegroundColor DarkCyan
    $previewLines | ForEach-Object { Write-Host "  $_" }
    Write-Host ""
} catch {
    Write-Host "[WARN] Unable to read preview from $enrichedPath : $($_.Exception.Message)" -ForegroundColor Yellow
}

# === Call the Python Notion pusher ===
# Expectation: nvda_bplus_push_to_notion.py reads the enriched JSONL and uses:
#   - NOTION_JOURNAL_DS for the Trading Journal data_source_id
#   - bar_replay_tag, kelly_f, gate_rank, etc. fields to populate columns
# If the CLI shape differs, adjust the arguments below accordingly.
& $py $pusher `
    --jsonl $enrichedPath

$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    throw "nvda_bplus_push_to_notion.py exited with code $exitCode."
}

Write-Host ""
Write-Host "[DONE] Pushed NVDA B+ enriched replay trades into Notion Trading Journal." -ForegroundColor Green
Write-Host "Source JSONL: $enrichedPath"