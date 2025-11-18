param(
    [int]$TopCount = 3
)

$ErrorActionPreference = 'Stop'

# 0) Go to repo root
Set-Location 'C:\Users\rhcy9\OneDrive\文件\HybridAITrading'

# Derive paths from current location (handles Unicode correctly)
$root      = Get-Location
$intelPath = Join-Path $root '.intel\yt_scalper_feed.jsonl'
$outDir    = Join-Path $root '.intel\yt_playbooks'

# 1) Load intel JSONL
if (-not (Test-Path $intelPath)) {
    Write-Warning "Intel file not found: $intelPath. Run: python .\tools\yt_scalper_feed.py"
    Read-Host "Press Enter to exit"
    return
}

$rows = @()
Get-Content $intelPath | ForEach-Object {
    if (-not $_) { return }
    try {
        $rows += ($_ | ConvertFrom-Json)
    } catch {
        # skip bad lines
    }
}

if (-not $rows -or $rows.Count -eq 0) {
    Write-Warning "No usable rows loaded from $intelPath."
    Read-Host "Press Enter to exit"
    return
}

# 2) Sort by score desc, then published_at desc
$rows = $rows | Sort-Object `
    @{ Expression = 'score'; Descending = $true }, `
    @{ Expression = 'published_at'; Descending = $true }

# 3) Select top N
if ($TopCount -lt 1) { $TopCount = 1 }
if ($TopCount -gt $rows.Count) { $TopCount = $rows.Count }

$top = $rows | Select-Object -First $TopCount

Write-Host "Selected top $TopCount videos for study:" -ForegroundColor Cyan
$i = 0
foreach ($r in $top) {
    $i++
    Write-Host ("{0}. [{1}] {2}" -f $i, $r.score, $r.title)
    Write-Host ("    {0}" -f $r.url)
    Write-Host ""
}

# 4) Open in browser (Step 3)
foreach ($r in $top) {
    Write-Host "Opening in browser: $($r.url)" -ForegroundColor Yellow
    Start-Process $r.url
}

# 5) Generate Markdown playbook templates (Step 4)
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$todayTag = (Get-Date).ToString('yyyyMMdd')
$mdEnc = New-Object System.Text.UTF8Encoding($false)

$i = 0
foreach ($row in $top) {
    $i++

    $safeTitle = ($row.title -replace '[^\w\-]+','_')
    if (-not $safeTitle) { $safeTitle = "video_$i" }

    $fileName = "{0}_{1}.md" -f $todayTag, $safeTitle
    $outPath = Join-Path $outDir $fileName

    $lines = @(
        "# YT Scalper Intel  $($row.title)"
        ""
        "- URL: $($row.url)"
        "- Channel: $($row.channel_title)"
        "- Published: $($row.published_at)"
        "- Score: $($row.score)"
        ""
        "## Setup Summary"
        "- Instrument(s): "
        "- Timeframe: "
        "- Context / Regime (trend / range / news): "
        "- Core idea / edge: "
        ""
        "## Entry Rules"
        "- Condition 1: "
        "- Condition 2: "
        "- Time-of-day filter: "
        ""
        "## Stop / Invalidation Rules"
        "- Hard stop placement: "
        "- Invalidation conditions: "
        "- What must NOT happen: "
        ""
        "## Target / Exit Logic"
        "- Primary target: "
        "- Scale-out / trail rules: "
        "- When to scratch: "
        ""
        "## Risk Notes"
        "- Max risk per trade (R or $): "
        "- Max trades per day for this setup: "
        "- News / volatility filters: "
        ""
        "## Bar Replay Notes"
        "- Date range replayed: "
        "- Number of trades in replay: "
        "- Win rate: "
        "- Net R / PnL (simulated): "
        "- Observed failure patterns: "
        ""
        "## Go/No-Go Decision for Live Hybrid AI"
        "- [ ] Approved playbook for Live"
        "- [ ] Needs more replay / refinement"
        "- [ ] Reject  do NOT trade live"
    )

    [System.IO.File]::WriteAllLines($outPath, $lines, $mdEnc)
    Write-Host "Created playbook template: $outPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "Done. Review videos, fill playbooks, then bring insights into Notion / Hybrid AI code." -ForegroundColor Cyan
Read-Host "Press Enter to return to PowerShell"