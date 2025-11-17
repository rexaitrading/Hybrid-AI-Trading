param(
    [string]$InputNews = ".intel\\news_feed.jsonl",
    [string]$Output    = "logs\\news_events.jsonl"
)

Write-Host "[Collect-NewsEvents] Source: $InputNews" -ForegroundColor Cyan
Write-Host "[Collect-NewsEvents] Target: $Output"   -ForegroundColor Cyan

if (-not (Test-Path $InputNews)) {
    Write-Host "[Collect-NewsEvents] Source news file not found, nothing to do." -ForegroundColor Yellow
    return
}

# Ensure output dir/file exist
$outDir = Split-Path -Parent $Output
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir | Out-Null
}
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
if (-not (Test-Path $Output)) {
    [System.IO.File]::WriteAllText($Output, "", $utf8NoBom)
    Write-Host "[Collect-NewsEvents] Created $Output" -ForegroundColor Green
}

$nowUtc = (Get-Date).ToUniversalTime().ToString("o")
$added = 0

function Get-Prop {
    param(
        [Parameter(Mandatory=$true)]$Record,
        [Parameter(Mandatory=$true)][string]$Name
    )
    $p = $Record.PSObject.Properties[$Name]
    if ($p) { return $p.Value }
    return $null
}

Get-Content -Path $InputNews | ForEach-Object {
    $line = $_
    if ([string]::IsNullOrWhiteSpace($line)) { return }

    try {
        $rec = $line | ConvertFrom-Json -ErrorAction Stop
    } catch {
        return
    }

    $obj = [ordered]@{}

    # --- timestamp ---
    $ts = Get-Prop -Record $rec -Name 'published_at'
    if (-not $ts) { $ts = Get-Prop -Record $rec -Name 'ts' }
    if (-not $ts) { $ts = Get-Prop -Record $rec -Name 'timestamp' }
    if (-not $ts) { $ts = $nowUtc }
    $obj.ts_news = $ts

    # --- symbol: derive from symbol/ticker/query ---
    $symbol = $null

    # (no symbol/ticker in your schema yet, but keep these for future)
    if (-not $symbol) { $symbol = Get-Prop -Record $rec -Name 'symbol' }
    if (-not $symbol) { $symbol = Get-Prop -Record $rec -Name 'ticker' }

    # Fallback: use first token of query as symbol
    if (-not $symbol) {
        $q = Get-Prop -Record $rec -Name 'query'
        if ($q) {
            $parts = $q -split '\s+'
            if ($parts.Count -gt 0) {
                $symbol = $parts[0].ToUpperInvariant()
            }
        }
    }

    if (-not $symbol) {
        # generic news we can't map; skip
        return
    }
    $obj.symbol = $symbol

    # --- headline/title ---
    $headline = $null
    if (-not $headline) { $headline = Get-Prop -Record $rec -Name 'title' }
    if (-not $headline) { $headline = Get-Prop -Record $rec -Name 'headline' }
    if (-not $headline) { $headline = "<no_headline>" }
    $obj.headline = $headline

    # --- source/provider ---
    $source = $null
    if (-not $source) { $source = Get-Prop -Record $rec -Name 'source' }
    if (-not $source) { $source = Get-Prop -Record $rec -Name 'provider' }
    if (-not $source) { $source = "news_feed" }

    $obj.source     = $source
    $obj.raw_source = "news_feed"
    $obj.ts_logged  = $nowUtc

    $json = ($obj | ConvertTo-Json -Compress -Depth 5)
    Add-Content -Path $Output -Value $json
    $added++
}

Write-Host "[Collect-NewsEvents] Appended $added record(s) into $Output" -ForegroundColor Green