[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$JsonlPath,

    [Parameter(Mandatory = $false)]
    [int]$Limit = 50,

    [Parameter(Mandatory = $false)]
    [switch]$DryRun,

    [Parameter(Mandatory = $false)]
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not (Test-Path $JsonlPath)) {
    throw "JSONL not found: $JsonlPath"
}

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $here "replay_trades_to_notion.py"

if (-not (Test-Path $scriptPath)) {
    throw "Notion replay script not found: $scriptPath"
}

if (-not $env:NOTION_TOKEN) {
    throw "NOTION_TOKEN environment variable is not set."
}

if (-not $env:NOTION_TRADE_DATA_SOURCE_ID -and -not $env:NOTION_TRADE_ID) {
    throw "Set either NOTION_TRADE_DATA_SOURCE_ID (preferred) or NOTION_TRADE_ID in the environment."
}

Write-Host "[Push-ReplayToNotion] Python: $PythonExe" -ForegroundColor Cyan
Write-Host "[Push-ReplayToNotion] JSONL:  $JsonlPath" -ForegroundColor Cyan
Write-Host "[Push-ReplayToNotion] Limit:   $Limit" -ForegroundColor Cyan
Write-Host "[Push-ReplayToNotion] DryRun:  $DryRun" -ForegroundColor Cyan

$arguments = @(
    $scriptPath,
    "--jsonl", $JsonlPath,
    "--limit", $Limit
)

if ($DryRun) {
    $arguments += "--dry-run"
}

& $PythonExe @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Replay->Notion script failed with exit code $LASTEXITCODE"
}

Write-Host "[Push-ReplayToNotion] Completed OK." -ForegroundColor Green