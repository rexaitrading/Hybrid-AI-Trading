param(
    [string]$NewsPath = "logs\\news_events.jsonl",
    [string]$Output   = "logs\\news_gate.jsonl",
    [string]$Date     = $(Get-Date).AddDays(-1).ToString("yyyy-MM-dd")  # default = yesterday
)

Write-Host "[Build-NewsGate] News:   $NewsPath" -ForegroundColor Cyan
Write-Host "[Build-NewsGate] Output: $Output"   -ForegroundColor Cyan
Write-Host "[Build-NewsGate] Date:   $Date"     -ForegroundColor Cyan

if (-not (Test-Path $NewsPath)) {
    Write-Host "[Build-NewsGate] News file not found, nothing to do." -ForegroundColor Yellow
    return
}

# Ensure output dir/file
$outDir = Split-Path -Parent $Output
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir | Out-Null
}
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($Output, "", $utf8NoBom)

# very simple keyword lists (can refine later)
$negativeWords = @(
    'plunge','tumble','drop','falls','sinks','slides','crash','bear',
    'warning','downgrade','cut','slump','panic','sell-off','fear'
)
$positiveWords = @(
    'soar','rally','surge','jumps','climb','record high','upgrade','beats',
    'bull','strong','momentum'
)

function Load-JsonLines {
    param([string]$Path)
    Get-Content -Path $Path | ForEach-Object {
        if ([string]::IsNullOrWhiteSpace($_)) { return }
        try {
            $_ | ConvertFrom-Json -ErrorAction Stop
        } catch { return }
    }
}

# 1) Load all news for the given date (by parsing ts_news)
$news = Load-JsonLines -Path $NewsPath | ForEach-Object {
    if (-not $_.ts_news) { return }
    try {
        $d = Get-Date $_.ts_news -ErrorAction Stop
        $recDate = $d.ToString('yyyy-MM-dd')
    } catch {
        $recDate = $null
    }
    if ($recDate -eq $Date) {
        $_
    }
}

if (-not $news) {
    Write-Host "[Build-NewsGate] No news events found for $Date in $NewsPath." -ForegroundColor Yellow
    return
}

# Group by symbol
$groups = $news | Where-Object { $_.symbol } | Group-Object -Property symbol

$nowUtc = (Get-Date).ToUniversalTime().ToString("o")
$written = 0

foreach ($g in $groups) {
    $sym   = $g.Name
    $items = $g.Group

    $neg = 0
    $pos = 0

    foreach ($item in $items) {
        $h = ($item.headline | Out-String).ToLowerInvariant()

        foreach ($w in $negativeWords) {
            if ($h -like "*$w*") { $neg++ ; break }
        }
        foreach ($w in $positiveWords) {
            if ($h -like "*$w*") { $pos++ ; break }
        }
    }

    $score = $pos - $neg

    # Simple risk flag logic (tune later)
    $flag = "OK"
    if ($neg -ge 2 -and $pos -lt $neg) { $flag = "BLOCK" }
    elseif ($neg -ge 1) { $flag = "CAUTION" }

    $obj = [ordered]@{
        date       = $Date
        symbol     = $sym
        news_count = $items.Count
        neg_count  = $neg
        pos_count  = $pos
        news_score = $score
        risk_flag  = $flag
        ts_logged  = $nowUtc
    }

    $json = ($obj | ConvertTo-Json -Compress -Depth 5)
    Add-Content -Path $Output -Value $json
    $written++
}

Write-Host "[Build-NewsGate] Wrote $written symbol gate record(s) into $Output" -ForegroundColor Green