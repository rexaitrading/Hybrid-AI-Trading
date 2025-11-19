param(
    [int]$Limit    = 0,
    [int]$TopN     = 10,
    [int]$MaxPages = 5
)

$ErrorActionPreference = 'Stop'

# Move to repo root (parent of tools)
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

Write-Host "=== NVDA B+ FULL PIPELINE ===" -ForegroundColor Cyan
Write-Host "[ROOT] $repoRoot" -ForegroundColor Cyan
Write-Host "[ARGS] Limit=$Limit TopN=$TopN MaxPages=$MaxPages" -ForegroundColor Cyan

$analytics = Join-Path $repoRoot 'tools\Run-NvdaBplusAnalytics.ps1'
$notion    = Join-Path $repoRoot 'tools\Run-NvdaBplusToNotion.ps1'

if (-not (Test-Path $analytics)) { throw "Not found: $analytics" }
if (-not (Test-Path $notion))    { throw "Not found: $notion"    }

Write-Host "" 
Write-Host ">>> STEP 1: Analytics (sweep + report) <<<" -ForegroundColor DarkCyan
& $analytics -Limit $Limit -TopN $TopN

Write-Host "" 
Write-Host ">>> STEP 2: Push trades to Notion <<<" -ForegroundColor DarkGreen
& $notion -Limit $Limit -MaxPages $MaxPages

Write-Host "" 
Write-Host "=== DONE: check Notion view [NVDA B+ GateScore (NEW)] ===" -ForegroundColor Green # ====================================================================
# [NVDA B+] Final step: sync replay outcomes into Notion (v2)
# Requires:
#   - tools\Update-NotionReplayOutcomes_v2.ps1
#   - research\nvda_bplus_replay_trades.jsonl (replay output)
# ====================================================================

Write-Host "=== [NVDA B+] Notion sync: Begin ==="

$notionUpdateScript = 'tools\Update-NotionReplayOutcomes_v2.ps1'
$replayJsonl        = 'research\nvda_bplus_replay_trades.jsonl'

if (-not (Test-Path $notionUpdateScript)) {
    Write-Warning "NVDA B+ Notion sync: missing script $notionUpdateScript  skipping Notion update."
} elseif (-not (Test-Path $replayJsonl)) {
    Write-Warning "NVDA B+ Notion sync: missing JSONL $replayJsonl  skipping Notion update."
} else {
    Write-Host "NVDA B+ Notion sync: using $replayJsonl via $notionUpdateScript"
    & $notionUpdateScript -JsonlPath $replayJsonl
}

Write-Host "=== [NVDA B+] Notion sync: End ==="
# ====================================================================



