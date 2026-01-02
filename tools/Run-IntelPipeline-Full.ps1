[CmdletBinding()]
param(
  [int]$LookbackMinutes = 60,
  [string]$IntelDir = "src\.intel",
  [string[]]$Symbols = @("NVDA","SPY","QQQ"),

  # IBKR news requires TWS/IBG. Keep OFF by default for IBG-off operation.
  [switch]$EnableIbkrNews
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$intelPath = Join-Path $repoRoot $IntelDir
if (-not (Test-Path $intelPath)) { New-Item -ItemType Directory -Path $intelPath -Force | Out-Null }

$newsOut = Join-Path $intelPath "news_feed.jsonl"
$ts = (Get-Date).ToUniversalTime().ToString("o")
Write-Host "[INTEL-FULL] tick ts_utc=$ts lookback_min=$LookbackMinutes out=$newsOut" -ForegroundColor Cyan

# --- (1) RSS news (IBG-off safe) ---
$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $py)) { throw "Python venv missing: $py" }
$env:PYTHONPATH = $repoRoot
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$rss = Join-Path $repoRoot "scripts\get_news_rss.py"

# --- (1b) YouTube feed (API key; IBG-off safe) ---
$ytOut = Join-Path $intelPath "youtube_feed.jsonl"
$yt = Join-Path $repoRoot "scripts\get_youtube_feed.py"
if (Test-Path $yt) {
  & $py $yt --out $ytOut --lookbackHours 48 --maxPerQuery 5 | Out-Host
} else {
  Write-Host "[INTEL-FULL] WARN: scripts\get_youtube_feed.py missing; skipping YouTube." -ForegroundColor Yellow
}

if (Test-Path $rss) {
  & $py $rss --out $newsOut --lookbackMin $LookbackMinutes --maxItems 50 | Out-Host
} else {
  Write-Host "[INTEL-FULL] WARN: scripts\get_news_rss.py missing; skipping RSS." -ForegroundColor Yellow
}


# --- (1) NEWS snapshot ---
# Default: IBG-OFF safe mode => skip IBKR news (because it needs IB host/port).
# When you want IBKR news, run with -EnableIbkrNews AND have IBG/TWS running.
if ($EnableIbkrNews) {
  $py = Join-Path $repoRoot ".venv\Scripts\python.exe"
  if (-not (Test-Path -LiteralPath $py)) { throw "Python venv missing: $py" }

  $env:PYTHONPATH = $repoRoot
  $env:PYTHONUTF8 = "1"
  $env:PYTHONIOENCODING = "utf-8"

  $newsPy = Join-Path $repoRoot "scripts\get_news.py"
  if (-not (Test-Path $newsPy)) { throw "Missing: $newsPy" }

  # IBKR news: single run, JSONL, write to file by redirecting stdout
  $symArgs = ($Symbols | ForEach-Object { $_.Trim().ToUpper() }) -join " "
  Write-Host "[INTEL-FULL] IBKR news enabled: symbols=$symArgs" -ForegroundColor Yellow

  $tmp = Join-Path $env:TEMP ("hat_news_" + [guid]::NewGuid().ToString("n") + ".jsonl")
  & $py $newsPy --lookbackMin $LookbackMinutes --poll 0 --json $Symbols *> $tmp
  if ($LASTEXITCODE -ne 0) { throw "get_news.py exit=$LASTEXITCODE" }

  if (Test-Path $tmp) {
    Get-Content $tmp -Encoding utf8 | Add-Content -LiteralPath $newsOut -Encoding utf8
    Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    Write-Host "[INTEL-FULL] wrote news_feed.jsonl (IBKR)" -ForegroundColor Green
  }
} else {
  Write-Host "[INTEL-FULL] IBKR news disabled (IBG-OFF mode). Skipping news collection this tick." -ForegroundColor DarkYellow
}

# --- (2) Always write minimal risk pulse (Phase-5 safety heartbeat) ---
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Run-IntelPipeline-Minimal.ps1")
if ($LASTEXITCODE -ne 0) { throw "intel_minimal exit=$LASTEXITCODE" }

Write-Host "[INTEL-FULL] done" -ForegroundColor Green
exit 0
