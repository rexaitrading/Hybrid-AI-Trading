param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = 'Stop'

# toolsDir = ...\HybridAITrading\tools
$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $toolsDir) { $toolsDir = Get-Location }

# root = ...\HybridAITrading
$root = Split-Path -Parent $toolsDir
Set-Location $root

# Hydrate YOUTUBE_API_KEY from User-level env for this process
$env:YOUTUBE_API_KEY = [Environment]::GetEnvironmentVariable('YOUTUBE_API_KEY','User')

Write-Host "=== STEP 1: Refresh intel (YouTube + Google News) ===" -ForegroundColor Cyan

& $PythonExe .\tools\yt_scalper_feed.py
& $PythonExe .\tools\news_feed.py

Write-Host ""
Write-Host "=== STEP 2: Review scalper education (YouTube) ===" -ForegroundColor Cyan
& $PythonExe .\tools\yt_scalper_pretty.py

Write-Host ""
Write-Host "=== STEP 3: Review macro / volatility / BTC / SPY regime (news) ===" -ForegroundColor Cyan
& $PythonExe .\tools\news_pretty.py

Write-Host ""
Write-Host "=== STEP 4: Auto-open top 3 YouTube scalper videos ===" -ForegroundColor Cyan

$rows = @()
Get-Content '.intel\yt_scalper_feed.jsonl' | ForEach-Object {
    if (-not $_) { return }
    try { $rows += ($_ | ConvertFrom-Json) } catch { }
}

if ($rows -and $rows.Count -gt 0) {
    $top = $rows | Sort-Object `
        @{Expression='score';Descending=$true}, `
        @{Expression='published_at';Descending=$true} `
        | Select-Object -First 3

    Write-Host "Opening top $($top.Count) YouTube scalper videos:" -ForegroundColor Cyan
    foreach ($r in $top) {
        Write-Host ("[score={0}] {1}" -f $r.score, $r.title)
        Write-Host ("    {0}" -f $r.url)
        Start-Process $r.url
    }
} else {
    Write-Host "No yt_scalper_feed rows found." -ForegroundColor Yellow
}