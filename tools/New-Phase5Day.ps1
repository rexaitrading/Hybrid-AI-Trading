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
$dateKey   = $today.ToString("yyyyMMdd")

$title     = "{0}  AAPL Phase5 LIVE ORB/VWAP" -f $todayStr
$logTag    = "[New-Phase5Day-AAPL]"

Write-Host "$logTag Creating page: $title" -ForegroundColor Cyan

# --- 3) Local idempotency flag (per symbol + date) --------------------------
$flagRoot = 'intel\notion_flags'
if (-not (Test-Path $flagRoot)) {
    New-Item -Path $flagRoot -ItemType Directory -Force | Out-Null
}

$flagPath = Join-Path $flagRoot ("phase5_AAPL_{0}.flag" -f $dateKey)

if (Test-Path $flagPath) {
    Write-Host "$logTag Flag already exists for today ($flagPath). Skipping create to avoid duplicate Phase5 row." -ForegroundColor Yellow
    return
}

# --- 4) Common headers -------------------------------------------------------
$headers = @{
    "Authorization"  = "Bearer $token"
    "Notion-Version" = "2025-09-03"
    "Content-Type"   = "application/json; charset=utf-8"
}

# --- 5) Build Notion page body ----------------------------------------------
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

# --- 6) Call Notion API ------------------------------------------------------
$response = Invoke-RestMethod `
    -Method Post `
    -Uri "https://api.notion.com/v1/pages" `
    -Headers $headers `
    -Body $json

if (-not $response.id) {
    throw "$logTag No page id returned from Notion."
}

Write-Host "$logTag Created page id: $($response.id)" -ForegroundColor Green
Write-Host "$logTag URL: $($response.url)" -ForegroundColor Green

# --- 7) Write success flag ---------------------------------------------------
try {
    Set-Content -Path $flagPath -Value $response.url -Encoding UTF8
    Write-Host "$logTag Wrote idempotency flag: $flagPath" -ForegroundColor Green
} catch {
    Write-Host "$logTag WARNING: Failed to write flag file ($flagPath). Error: $($_.Exception.Message)" -ForegroundColor Yellow
}