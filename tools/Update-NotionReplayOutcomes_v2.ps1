param(
    [string]$JsonlPath = "research\nvda_bplus_replay_trades.jsonl"
)

$ErrorActionPreference = "Stop"

$dataSourceId = "2970bf31-ef15-809e-802a-000b4911c1fc"

if (-not $env:HAT_NOTION_API_KEY) {
    throw "HAT_NOTION_API_KEY not set."
}

$headers = @{
    "Authorization"  = "Bearer $($env:HAT_NOTION_API_KEY)"
    "Notion-Version" = "2025-09-03"
}

Write-Host "=== Update-NotionReplayOutcomes_v2.ps1 (LOGGED) ==="
Write-Host "JSONL: $JsonlPath"
Write-Host ""

if (-not (Test-Path $JsonlPath)) {
    Write-Warning ("JSONL file not found: {0} (continuing, but updates will likely be skipped)." -f $JsonlPath)
} else {
    Write-Host ("Found JSONL file: {0}" -f $JsonlPath)
}

Write-Host "Step 1: Fetching pages from Notion data source..."
Write-Host ""

$allPages     = @()
$startCursor  = $null
$pageIndex    = 0
$maxPages     = 50
$seenCursors  = @()

do {
    $pageIndex++

    $body = @{ page_size = 100 }
    if ($startCursor) { $body.start_cursor = $startCursor }

    $resp = Invoke-RestMethod `
        -Uri "https://api.notion.com/v1/data_sources/$dataSourceId/query" `
        -Headers $headers `
        -Method Post `
        -Body ($body | ConvertTo-Json -Depth 5)

    $countThisPage = 0
    if ($resp.results) {
        $countThisPage = $resp.results.Count
        $allPages      += $resp.results
    }

    Write-Host ("Page {0}: results={1} has_more={2} next_cursor={3}" -f `
        $pageIndex, $countThisPage, $resp.has_more, $resp.next_cursor)

    if ($resp.next_cursor) {
        if ($seenCursors -contains $resp.next_cursor) {
            Write-Warning ("Cursor loop detected at next_cursor={0}. Breaking pagination loop." -f $resp.next_cursor)
            break
        }
        $seenCursors += $resp.next_cursor
        $startCursor = $resp.next_cursor
    } else {
        $startCursor = $null
    }

    if (-not $resp.has_more) {
        Write-Host "No more pages from Notion (has_more = False)."
        break
    }

    if ($pageIndex -ge $maxPages) {
        Write-Warning ("Reached max page limit ({0}). Breaking pagination loop." -f $maxPages)
        break
    }

    Write-Host ""
} while ($true)

Write-Host ""
Write-Host ("Finished Notion fetch: pages={0}, total rows={1}" -f $pageIndex, $allPages.Count)
Write-Host ""

$tagToPageId = @{}

foreach ($p in $allPages) {
    $tagProp = $p.properties.bar_replay_tag
    if ($tagProp -and $tagProp.select) {
        $tag = $tagProp.select.name
        if ($tag) {
            $tagToPageId[$tag] = $p.id
        }
    }
}

Write-Host ("Tag map entries: {0}" -f $tagToPageId.Count)
Write-Host ""

$updated = 0
$skipped = 0

$lines = Get-Content $JsonlPath
$totalLines = $lines.Count

Write-Host ("Step 2: Updating Notion pages from JSONL. Lines={0}" -f $totalLines)
Write-Host ""

$lineIndex = 0

$lines | ForEach-Object {
    $lineIndex++
    $line = $_.Trim()
    if (-not $line) { return }

    $obj = $line | ConvertFrom-Json

    $tag = $obj.bar_replay_tag
    if (-not $tag) {
        Write-Warning ("Skipping line {0}: no bar_replay_tag in JSON." -f $lineIndex)
        $skipped++
        return
    }

    if (-not $tagToPageId.ContainsKey($tag)) {
        Write-Warning ("No Notion page found for tag '{0}' (line {1})  skipping." -f $tag, $lineIndex)
        $skipped++
        return
    }

    $pageId = $tagToPageId[$tag]

    $grossRaw = $obj.gross_pnl_pct
    $gross    = $null
    if ($grossRaw -ne $null -and $grossRaw -ne "") {
        [double]::TryParse($grossRaw.ToString(), [ref]$gross) | Out-Null
    }

    $outcome = "FLAT"
    if ($gross -gt 0) {
        $outcome = "WIN"
    }
    elseif ($gross -lt 0) {
        $outcome = "LOSS"
    }

    $edgeBucket = $obj.gate_bucket
    if (-not $edgeBucket) { $edgeBucket = "UNKNOWN" }

    $payload = @{
        properties = @{
            Outcome = @{
                select = @{ name = $outcome }
            }
            EdgeBucket = @{
                select = @{ name = $edgeBucket }
            }
        }
    }

    $body = $payload | ConvertTo-Json -Depth 5
    $uri  = "https://api.notion.com/v1/pages/$pageId"

    try {
        Invoke-RestMethod -Uri $uri -Method Patch -Headers $headers -Body $body | Out-Null
        $updated++
        Write-Host ("OK line={0} tag={1} -> Outcome={2}, EdgeBucket={3}" -f `
            $lineIndex, $tag, $outcome, $edgeBucket)
    }
    catch {
        Write-Warning ("FAILED line={0} tag={1} page={2} : {3}" -f `
            $lineIndex, $tag, $pageId, $_.Exception.Message)
        $skipped++
    }

    if (($lineIndex % 10) -eq 0) {
        Write-Host ("Progress: {0}/{1} lines processed (updated={2}, skipped={3})" -f `
            $lineIndex, $totalLines, $updated, $skipped)
    }
}

Write-Host ""
Write-Host ("Done. Updated: {0}, Skipped: {1}" -f $updated, $skipped)
