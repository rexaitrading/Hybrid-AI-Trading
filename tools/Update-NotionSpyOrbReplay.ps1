[CmdletBinding()]
param(
    # Optional DateTag (yyyyMMdd). If omitted, use latest SPY ORB JSONL.
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

if (-not (Test-Path $py)) {
    throw "Python not found: $py"
}
if (-not (Test-Path $pusher)) {
    throw "SPY ORB Notion pusher not found: $pusher"
}
if (-not (Test-Path $replayOut)) {
    throw "replay_out folder not found: $replayOut. Run Run-SpyOrbReplay.ps1 first."
}

# Resolve which JSONL to use
$jsonlPath = $null

if ($DateTag) {
    $candidate = Join-Path $replayOut ("spy_orb_trades_{0}.jsonl" -f $DateTag)
    if (-not (Test-Path $candidate)) {
        throw "SPY ORB JSONL for DateTag '$DateTag' not found: $candidate. Run Run-SpyOrbReplay.ps1 -DateTag $DateTag first."
    }
    $jsonlPath = $candidate
} else {
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

try {
    $preview = Get-Content -LiteralPath $jsonlPath -TotalCount 2
    Write-Host "[PREVIEW] First line(s):" -ForegroundColor DarkCyan
    $preview | ForEach-Object { Write-Host "  $_" }
    Write-Host ""
} catch {
    Write-Host "[WARN] Unable to preview $jsonlPath : $($_.Exception.Message)" -ForegroundColor Yellow
}

$argsList = @(
    '--jsonl', $jsonlPath
)

if ($DryRun.IsPresent) {
    $argsList += '--dry-run'
}

Write-Host "[INFO] Calling spy_orb_push_to_notion.py..." -ForegroundColor Green

& $py $pusher @argsList

$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    throw "spy_orb_push_to_notion.py exited with code $exitCode."
}

Write-Host ""
Write-Host "[DONE] Pushed SPY ORB replay trades into Notion Trading Journal (dry_run=$DryRun)." -ForegroundColor Green
Write-Host "Source JSONL: $jsonlPath"