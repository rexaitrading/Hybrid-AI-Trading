param(
  [string]$NamePrefix = "Smoke OK",
  [string]$IsoWhen    = (Get-Date).ToString("s")
)
$ErrorActionPreference = 'Stop'

if (-not $env:NOTION_TOKEN)     { throw "Set `$env:NOTION_TOKEN first" }

# Load saved IDs (if present)
$idsPath = Join-Path (Resolve-Path 'config').Path 'notion_ids.json'
if (Test-Path $idsPath) {
  $ids = Get-Content $idsPath -Raw | ConvertFrom-Json
  $dsDashed = $ids.data_source_id
  $dbDashed = $ids.database_id
} else {
  # Fall back to env vars if file missing
  $dsDashed = if ($env:NOTION_DS_TRADES) { $env:NOTION_DS_TRADES.Insert(8,'-').Insert(13,'-').Insert(18,'-').Insert(23,'-') } else { $null }
  $dbDashed = if ($env:NOTION_DB_TRADES) { $env:NOTION_DB_TRADES.Insert(8,'-').Insert(13,'-').Insert(18,'-').Insert(23,'-') } else { $null }
}

if (-not $dsDashed -and -not $dbDashed) { throw "No data_source_id or database_id available. Run resolve_and_save_ids.ps1 first." }

$hdr = @{
  'Authorization'  = "Bearer $env:NOTION_TOKEN"
  'Notion-Version' = '2025-09-03'   # needed for data_sources & multi-source DBs
  'Content-Type'   = 'application/json'
}

$parent = if ($dsDashed) { @{ data_source_id = $dsDashed } } else { @{ database_id = $dbDashed } }

$body = @{
  parent     = $parent
  properties = @{
    Name = @{ title = @(@{ text = @{ content = "$NamePrefix $IsoWhen" }}) }
    ts   = @{ date  = @{ start = $IsoWhen } }
  }
} | ConvertTo-Json -Depth 10

$res = Invoke-RestMethod -Uri "https://api.notion.com/v1/pages" -Headers $hdr -Method POST -Body $body
"CREATE OK: $($res.id) -> $($res.url)"
