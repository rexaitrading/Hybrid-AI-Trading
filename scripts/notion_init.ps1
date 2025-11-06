param(
  [Parameter(Mandatory=$false)] [string]$ParentPageId = ""
)
$ErrorActionPreference='Stop'
if (-not $env:NOTION_TOKEN) { throw "Set $env:NOTION_TOKEN first." }

# If you already set NOTION_DB_REPLAYS, just verify and exit
if ($env:NOTION_DB_REPLAYS) {
  try {
    $h=@{"Authorization"="Bearer $($env:NOTION_TOKEN)";"Notion-Version"="2022-06-28"}
    $db = Invoke-RestMethod -Method GET -Uri ("https://api.notion.com/v1/databases/{0}" -f $env:NOTION_DB_REPLAYS) -Headers $h
    "Ã¢Å“â€ NOTION_DB_REPLAYS OK: $($db.title.plain_text -join ' ')"
    exit 0
  } catch {
    Write-Host "WARN: NOTION_DB_REPLAYS invalid or not accessible. Creating new DB..." -ForegroundColor Yellow
  }
}

if (-not $ParentPageId) { throw "Provide -ParentPageId <your workspace page id> to create a DB." }

$headers = @{
  "Authorization"  = "Bearer $($env:NOTION_TOKEN)"
  "Notion-Version" = "2022-06-28"
  "Content-Type"   = "application/json"
}

$body = @{
  parent     = @{ type="page_id"; page_id = $ParentPageId }
  title      = @(@{ type="text"; text=@{ content="Trading Journal (Replays)" }})
  properties = @{
    "Date"          = @{ "date" = @{} }
    "Symbol"        = @{ "title" = @{} }
    "Mode"          = @{ "select" = @{ "options" = @(@{name="auto"}, @{name="step"}) } }
    "ORB Minutes"   = @{ "number" = @{ "format"="number" } }
    "Qty"           = @{ "number" = @{ "format"="number" } }
    "Entry"         = @{ "number" = @{ "format"="number" } }
    "Exit"          = @{ "number" = @{ "format"="number" } }
    "PnL"           = @{ "number" = @{ "format"="dollar" } }
    "Fees"          = @{ "number" = @{ "format"="dollar" } }
    "Trade ID"      = @{ "rich_text" = @{} }
    "Pattern"       = @{ "multi_select" = @{ "options" = @(@{name="ORB Break"}, @{name="Retest"}, @{name="VWAP Bounce"}) } }
    "Notes"         = @{ "rich_text" = @{} }
    "Screenshot"    = @{ "url" = @{} }
    "Replay Link"   = @{ "url" = @{} }
  }
} | ConvertTo-Json -Depth 8

$res = Invoke-RestMethod -Method POST -Uri "https://api.notion.com/v1/databases" -Headers $headers -Body $body
$env:NOTION_DB_REPLAYS = $res.id
"Ã¢Å“â€ Created NOTION_DB_REPLAYS: $($res.id)"
