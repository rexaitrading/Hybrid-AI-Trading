[CmdletBinding()]
param(
    [string]$DateTag,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptRoot = $PSScriptRoot
$repoRoot   = Split-Path -Parent $scriptRoot

Set-Location $repoRoot

$py        = '.venv\Scripts\python.exe'
$pusher    = Join-Path $repoRoot 'tools\spy_orb_push_to_notion.py'
$replayOut = Join-Path $repoRoot 'replay_out'

if (-not (Test-Path $py))      { throw "Python not found: $py" }
if (-not (Test-Path $pusher))  { throw "SPY ORB Notion pusher not found: $pusher" }
if (-not (Test-Path $replayOut)) { throw "replay_out folder not found: $replayOut. Run Run-SpyOrbReplay.ps1 first." }

# Resolve which JSONL to use
$jsonlPath = $null

if ($DateTag) {
    # 1) Try ORB-specific filename using env ORB_MINUTES/TP_R, if set
    $orbMin = $env:ORB_MINUTES
    $tpR    = $env:TP_R
    $orbCandidate = $null
    if ($orbMin -and $tpR) {
        $orbCandidate = Join-Path $replayOut ("spy_orb_trades_{0}_orb{1}_tp{2}.jsonl" -f $DateTag, $orbMin, $tpR)
    }

    $baseCandidate = Join-Path $replayOut ("spy_orb_trades_{0}.jsonl" -f $DateTag)

    if ($orbCandidate -and (Test-Path $orbCandidate)) {
        $jsonlPath = $orbCandidate
    } elseif (Test-Path $baseCandidate) {
        $jsonlPath = $baseCandidate
    } else {
        throw "SPY ORB JSONL for DateTag '$DateTag' not found (tried $orbCandidate and $baseCandidate). Run Run-SpyOrbReplay.ps1 -DateTag $DateTag first."
    }
}
else {
    # No DateTag: pick the most recent spy_orb_trades_* JSONL (ORB-specific or base)
    $pattern = 'spy_orb_trades_*.jsonl'
    $files = Get-ChildItem -Path $replayOut -Filter $pattern -File |
             Sort-Object LastWriteTime -Descending
    if (-not $files -or $files.Count -eq 0) {
        throw "No SPY ORB JSONL files found under $replayOut with pattern $pattern."
    }
    $jsonlPath = $files[0].FullName
}

Write-Host "=== Update-NotionSpyOrbReplay ===" -ForegroundColor Cyan
Write-Host "Repo root        : $repoRoot"
Write-Host "SPY ORB JSONL    : $jsonlPath"
Write-Host "NOTION_JOURNAL_DS: $($env:NOTION_JOURNAL_DS)"
Write-Host ""

# If file is empty (0 bytes), nothing to push -> return gracefully
$info = Get-Item $jsonlPath
if ($info.Length -eq 0) {
    Write-Host "[WARN] SPY ORB JSONL is empty (no trades), skipping Notion push." -ForegroundColor Yellow
    return
}

try {
    $preview = Get-Content -LiteralPath $jsonlPath -TotalCount 2
    Write-Host "[PREVIEW] First line(s):" -ForegroundColor DarkCyan
    $preview | ForEach-Object { Write-Host "  $_" }
    Write-Host ""
} catch {
    Write-Host "[WARN] Unable to preview $jsonlPath : $($_.Exception.Message)" -ForegroundColor Yellow
}

$argsList = @('--jsonl',$jsonlPath)
if ($DryRun.IsPresent) { $argsList += '--dry-run' }

Write-Host "[INFO] Calling spy_orb_push_to_notion.py..." -ForegroundColor Green
& $py $pusher @argsList

$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    throw "spy_orb_push_to_notion.py exited with code $exitCode."
}

Write-Host ""
Write-Host "[DONE] Pushed SPY ORB replay trades into Notion Trading Journal (dry_run=$DryRun)." -ForegroundColor Green
Write-Host "Source JSONL: $jsonlPath"