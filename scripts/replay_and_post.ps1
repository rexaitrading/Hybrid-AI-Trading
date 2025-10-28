param(
    [string] $Universe = "AAPL,MSFT",
    [int]    $Bars     = 60,
    [int]    $Speed    = 10,
    [switch] $Post,          # if set: real Notion post; otherwise simulate
    [switch] $SkipSeed,      # if set: do not (re)seed synthetic data
    [switch] $Rotate,        # rotate logs by default (see below)
    [string] $DataDir        # optional override; defaults to <repo>\data
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# ---- Resolve repo root and key paths ----
$ScriptDir = $PSScriptRoot                 # ...\scripts
$Root      = Split-Path -Parent $ScriptDir # ...\HybridAITrading
if (-not $DataDir) { $DataDir = Join-Path $Root 'data' }

$Py        = Join-Path $Root '.\ .venv\Scripts\python.exe'.Replace(' ','')
$ReplayPy  = Join-Path $Root 'src\hybrid_ai_trading\replay\replay_engine.py'
$PosterPy  = Join-Path $Root 'src\hybrid_ai_trading\replay\notion_poster.py'
$ReplayCsv = Join-Path $Root 'logs\replay_journal.csv'
$ReplayLog = Join-Path $Root 'logs\replay_journal.jsonl'
$LogsDir   = Split-Path $ReplayLog

if (-not (Test-Path $Py))       { throw "Python not found at $Py (activate or create .venv)." }
if (-not (Test-Path $ReplayPy)) { throw "Missing $ReplayPy (replay_engine.py not found)." }
New-Item -ItemType Directory -Force -Path $DataDir,$LogsDir | Out-Null

# ---- Default rotate ON unless explicitly disabled ----
if (-not $PSBoundParameters.ContainsKey('Rotate')) { $Rotate = $true }
if ($Rotate) {
    if (Test-Path $ReplayCsv) { Rename-Item $ReplayCsv (Join-Path $LogsDir ('replay_journal.{0}.csv' -f (Get-Date -Format 'yyyyMMdd_HHmmss'))) -Force }
    if (Test-Path $ReplayLog) { Rename-Item $ReplayLog (Join-Path $LogsDir ('replay_journal.{0}.jsonl' -f (Get-Date -Format 'yyyyMMdd_HHmmss'))) -Force }
}

# ---- Seed synthetic bars (UTF-8 without BOM) unless skipped ----
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function New-SyntheticBars {
    param(
        [Parameter(Mandatory=$true)] [string] $Symbol,
        [int]    $Count = 60,
        [double] $Start = 100.0,
        [string] $OutDir,
        [Parameter(Mandatory=$true)] [System.Text.Encoding] $Encoding
    )
    if (-not $OutDir) { throw "New-SyntheticBars: -OutDir is required" }

    $rnd   = [Random]::new()
    $rows  = New-Object System.Collections.Generic.List[string]
    $rows.Add('ts,open,high,low,close,volume')
    $px = $Start

    for ($i=0; $i -lt $Count; $i++) {
        # chronological: oldest ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ newest
        $t     = (Get-Date).ToUniversalTime().AddMinutes($i - ($Count - 1))
        $step  = ($rnd.NextDouble() - 0.5) * 0.6
        $open  = [math]::Round($px, 2)
        $mid   = $open + $step
        $spread= [math]::Abs(($rnd.NextDouble() - 0.5) * 0.8)
        $high  = [math]::Round(([math]::Max($open,$mid) + $spread/2), 2)
        $low   = [math]::Round(([math]::Min($open,$mid) - $spread/2), 2)
        if ($low -gt $high) { $tmp=$low; $low=$high; $high=$tmp }
        $close = [math]::Round(($low + $high)/2, 2)
        $vol   = [int](80000 + $rnd.Next(0,120000))
        $rows.Add( ('{0},{1},{2},{3},{4},{5}' -f $t.ToString('s'), $open, $high, $low, $close, $vol) )
        $px = $close
    }

    $outPath = Join-Path $OutDir "$Symbol.csv"
    [System.IO.File]::WriteAllLines($outPath, $rows, $Encoding)
    Write-Host "[data] Wrote $Count bars (UTF8-NoBOM) -> $outPath"
}

if (-not $SkipSeed) {
    New-SyntheticBars -Symbol 'AAPL' -Count $Bars -Start 188.0 -OutDir $DataDir -Encoding $Utf8NoBom
    New-SyntheticBars -Symbol 'MSFT' -Count $Bars -Start 420.0 -OutDir $DataDir -Encoding $Utf8NoBom
}

# ---- Build replay args; include config/replay.yaml if present ----
$ReplayArgs = @(
    $ReplayPy,
    '--universe',   $Universe,
    '--data-dir',   $DataDir,
    '--speed',      $Speed.ToString(),
    '--limit',      $Bars.ToString(),
    '--journal-csv',$ReplayCsv,
    '--log-file',   $ReplayLog
)
$ConfigPath = Join-Path $Root 'config\replay.yaml'
if (Test-Path $ConfigPath) {
    $ReplayArgs += @('--config', $ConfigPath)
    Write-Host "[replay] Using config -> $ConfigPath"
}

# ---- Run replay_engine ----
$env:PYTHONPATH = (Join-Path $Root 'src') + ';' + $env:PYTHONPATH
& $Py @ReplayArgs

# ---- Verify outputs ----
if (-not (Test-Path $ReplayCsv)) { throw "Replay failed: $ReplayCsv not created" }
$csv = Get-Content -LiteralPath $ReplayCsv
if ($csv.Count -lt 2) { throw "Replay CSV has no data rows (lines=$($csv.Count))" }
Write-Host "[ok] CSV ready ($($csv.Count) lines): $ReplayCsv" -ForegroundColor Green
if (Test-Path $ReplayLog) {
    Write-Host ("--- Tail of {0} ---" -f (Split-Path $ReplayLog -Leaf))
    Get-Content $ReplayLog -Tail 5
}
Write-Host ("--- Tail of {0} ---" -f (Split-Path $ReplayCsv -Leaf))
$csv | Select-Object -Last 10

# ---- Notion poster (optional) ----
if ((Test-Path $PosterPy) -and $env:NOTION_TOKEN -and $env:NOTION_DB_ID) {
    if ($Post) {
        & $Py $PosterPy '--csv' $ReplayCsv '--limit' '100' '--rate' '2' | Out-Host
        Write-Host "Posted up to 100 rows to Notion (idempotent via external_id)." -ForegroundColor Green
    } else {
        & $Py $PosterPy '--csv' $ReplayCsv '--simulate' | Out-Host
        Write-Host "Simulated Notion post (no writes). Use -Post to push." -ForegroundColor Yellow
    }
} else {
    Write-Host "Notion posting skipped (set NOTION_TOKEN & NOTION_DB_ID, ensure notion_poster.py exists) or pass -Post to send." -ForegroundColor Yellow
}
