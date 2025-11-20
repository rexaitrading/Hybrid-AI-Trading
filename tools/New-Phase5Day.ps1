[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# --- 1) Load env vars -------------------------------------------------------
$token = $env:NOTION_TOKEN
$dsId  = $env:NOTION_JOURNAL_DS

if (-not $token) {
    throw "NOTION_TOKEN is not set (use [Environment]::SetEnvironmentVariable)."
}
if (-not $dsId) {
    throw "NOTION_JOURNAL_DS is not set."
}

# Some older boxes need this:
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# --- 2) Build title + date ---------------------------------------------------
$today     = Get-Date
$todayStr  = $today.ToString("yyyy-MM-dd")
$title     = "{0}  AAPL Phase5 LIVE ORB/VWAP" -f $todayStr

Write-Host "[New-Phase5Day] Creating page: $title" -ForegroundColor Cyan

# --- 3) Common headers -------------------------------------------------------
$headers = @{
    "Authorization"  = "Bearer $token"
    "Notion-Version" = "2025-09-03"
    "Content-Type"   = "application/json; charset=utf-8"
}

# --- 4) Build Notion page body ----------------------------------------------
# Assumes Trading Journal data source has properties:
# - Name    (title)
# - symbol  (rich_text)  -> "AAPL"
# - Phase   (select)     -> "Phase 5  LIVE"
# - Today   (date)

$body = @{
    parent     = @{
        data_source_id = $dsId
    }
    properties = @{
        "Name" = @{
            title = @(
                @{
                    text = @{
                        content = $title
                    }
                }
            )
        }
        "symbol" = @{
            rich_text = @(
                @{
                    text = @{
                        content = "AAPL"
                    }
                }
            )
        }
        "Phase" = @{
            select = @{
                name = "Phase 5  LIVE"
            }
        }
        "Today" = @{
            date = @{
                start = $todayStr
            }
        }
    }
}

$json = $body | ConvertTo-Json -Depth 5

# --- 5) Call Notion API ------------------------------------------------------
$response = Invoke-RestMethod `
    -Method Post `
    -Uri "https://api.notion.com/v1/pages" `
    -Headers $headers `
    -Body $json

if (-not $response.id) {
    throw "[New-Phase5Day] No page id returned from Notion."
}

Write-Host "[New-Phase5Day] Created page id: $($response.id)" -ForegroundColor Green
Write-Host "[New-Phase5Day] URL: $($response.url)" -ForegroundColor Green