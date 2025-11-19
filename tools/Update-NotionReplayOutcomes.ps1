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

Write-Host "=== Update-NotionReplayOutcomes.ps1 ==="
Write-Host "JSONL: $JsonlPath"
Write-Host ""

$allPages    = @()
$startCursor = $null

do {
    $body = @{ page_size = 50 }
    if ($startCursor) { $body.start_cursor = $startCursor }

    $resp = Invoke-RestMethod `
        -Uri "https://api.notion.com/v1/data_sources/$dataSourceId/query" `
        -Headers $headers `
        -Method Post `
        -Body ($body | ConvertTo-Json -Depth 5)

    $allPages    += $resp.results
    $startCursor  = $resp.next_cursor
} while ($resp.has_more)

Write-Host "Fetched" $allPages.Count "pages from Notion data source."

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

Write-Host "Tag map entries:" $tagToPageId.Count

$updated = 0
$skipped = 0

Get-Content $JsonlPath | ForEach-Object {
    $line = $_.Trim()
    if (-not $line) { return }

    $obj = $line | ConvertFrom-Json

    $tag = $obj.bar_replay_tag
    if (-not $tag) {
        Write-Warning "Skipping line: no bar_replay_tag in JSON."
        $skipped++
        return
    }

    if (-not $tagToPageId.ContainsKey($tag)) {
        Write-Warning "No Notion page found for tag '$tag'  skipping."
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
        Write-Host "OK tag=$tag -> Outcome=$outcome, EdgeBucket=$edgeBucket"
    }
    catch {
        Write-Warning "FAILED tag=$tag page=$pageId : $($_.Exception.Message)"
        $skipped++
    }
}

Write-Host ""
Write-Host "Done. Updated: $updated, Skipped: $skipped"
