Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
Set-Location $root

Write-Host "[HybridAITrading] Running Intel Feeds (YouTube + News)..." -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    $venvPy = Join-Path $root ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPy)) {
        throw "python not on PATH and .venv not found at $venvPy"
    }
    $env:PATH = (Split-Path $venvPy) + ";" + $env:PATH
}

function Invoke-PyIfExists {
    param(
        [string]$RelPath
    )
    $full = Join-Path $root $RelPath
    if (-not (Test-Path $full)) {
        Write-Host "[IntelFeeds] Missing: $RelPath" -ForegroundColor Yellow
        return
    }
    Write-Host "[IntelFeeds] python $RelPath" -ForegroundColor DarkGray
    & python $full
}

Invoke-PyIfExists -RelPath "tools\yt_scalper_feed.py"
Invoke-PyIfExists -RelPath "tools\yt_scalper_pretty.py"
Invoke-PyIfExists -RelPath "tools\news_feed.py"
Invoke-PyIfExists -RelPath "tools\news_pretty.py"

Write-Host "[HybridAITrading] Intel Feeds complete (check .intel/*.jsonl and pretty outputs)." -ForegroundColor Green
