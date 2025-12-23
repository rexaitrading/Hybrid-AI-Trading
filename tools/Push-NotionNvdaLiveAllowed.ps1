[CmdletBinding()]
param(
  [string]$PayloadPath = ".\logs\notion\nvda_live_allowed_payload.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "Test-NotionDbVisible.ps1") -DatabaseIdEnv NOTION_DB_DAYS_NVDA_LIVE_ALLOWED

function Resolve-RepoPath {
  param([string]$Path)
  $repoRoot = Split-Path -Parent $PSScriptRoot
  if([System.IO.Path]::IsPathRooted($Path)){ return $Path }
  return (Join-Path $repoRoot $Path)
}

function Read-Json {
  param([string]$Path)
  $full = Resolve-RepoPath $Path
  if(-not (Test-Path $full)){ throw "Missing file: $Path (resolved: $full)" }
  return (Get-Content -LiteralPath $full -Raw -Encoding utf8 | ConvertFrom-Json)
}

function Invoke-Notion {
  param(
    [Parameter(Mandatory=$true)][ValidateSet("GET","POST","PATCH")][string]$Method,
    [Parameter(Mandatory=$true)][string]$Url,
    [Parameter(Mandatory=$false)][object]$Body = $null
  )

  $token = [System.Environment]::GetEnvironmentVariable("NOTION_TOKEN","User")
  if(-not $token){ throw "NOTION_TOKEN missing (User env)" }

  $headers = @{
    "Authorization"  = "Bearer $token"
    "Notion-Version" = "2022-06-28"
    "Content-Type"   = "application/json"
  }

  if($null -eq $Body){
    return Invoke-RestMethod -Method $Method -Uri $Url -Headers $headers
  }

  $json = ($Body | ConvertTo-Json -Depth 20)
  return Invoke-RestMethod -Method $Method -Uri $Url -Headers $headers -Body $json
}

# ---- MAIN ----
$db = [System.Environment]::GetEnvironmentVariable("NOTION_DB_DAYS_NVDA_LIVE_ALLOWED","User")
if(-not $db){ throw "NOTION_DB_DAYS_NVDA_LIVE_ALLOWED missing (User env)" }

$payload = Read-Json -Path $PayloadPath
$asOf = ($payload.as_of_date + "").Trim()
if(-not $asOf){ throw "Payload missing as_of_date" }

# Property names in Notion DB (you can rename DB columns later; keep these stable for now)
# Recommended Notion property types:
# - Date: "date"
# - Checkbox: "NVDA Live Allowed", "NVDA BlockG Ready", "Phase4 OK", "EV Hard OK", "GateScore OK"
# - Rich text: "Reasons"
# - Rich text: "Stamp Path", "Contract Path"
# - Title: "Name" (required by Notion)
$props = @{
  "Name" = @{ "title" = @(@{ "text" = @{ "content" = ("NVDA Live Allowed " + $asOf) } }) }
  "date" = @{ "date" = @{ "start" = $asOf } }

  "NVDA Live Allowed" = @{ "checkbox" = [bool]$payload.nvda_live_allowed }

  "NVDA BlockG Ready" = @{ "checkbox" = [bool]$payload.nvda_blockg_ready }
  "SPY BlockG Ready"  = @{ "checkbox" = [bool]$payload.spy_blockg_ready }
  "QQQ BlockG Ready"  = @{ "checkbox" = [bool]$payload.qqq_blockg_ready }

  "Phase4 OK"       = @{ "checkbox" = [bool]$payload.phase4_ok_today }
  "EV Hard OK"      = @{ "checkbox" = [bool]$payload.ev_hard_daily_ok_today }
  "Phase23 OK"      = @{ "checkbox" = [bool]$payload.phase23_health_ok_today }
  "GateScore Fresh" = @{ "checkbox" = [bool]$payload.gatescore_fresh_today }
  "GateScore Samples OK" = @{ "checkbox" = [bool]$payload.gatescore_samples_ok }
  "GateScore Threshold OK" = @{ "checkbox" = [bool]$payload.gatescore_threshold_ok_today }
  "GateScore OK"    = @{ "checkbox" = [bool]$payload.gatescore_ok_today }

  "Reasons" = @{ "rich_text" = @(@{ "text" = @{ "content" = ((@($payload.reasons_not_ready) -join "; ") + "") } }) }

  "Contract Path" = @{ "rich_text" = @(@{ "text" = @{ "content" = ($payload.paths.blockg_status + "") } }) }
  "Stamp Path"    = @{ "rich_text" = @(@{ "text" = @{ "content" = ($payload.paths.nvda_stamp + "") } }) }
}

# 1) Query existing page by date == $asOf
$qBody = @{
  "filter" = @{
    "property" = "date"
    "date"     = @{ "equals" = $asOf }
  }
  "page_size" = 5
}

$q = Invoke-Notion -Method POST -Url ("https://api.notion.com/v1/databases/{0}/query" -f $db) -Body $qBody

$pageId = $null
try {
  if($q.results -and $q.results.Count -gt 0){
    $pageId = $q.results[0].id
  }
} catch { $pageId = $null }

if($pageId){
  # Update existing page
  $uBody = @{ "properties" = $props }
  [void](Invoke-Notion -Method PATCH -Url ("https://api.notion.com/v1/pages/{0}" -f $pageId) -Body $uBody)
  Write-Host ("[NOTION] UPDATED page for {0} id={1}" -f $asOf,$pageId) -ForegroundColor Green
  exit 0
}

# 2) Create new page
$cBody = @{
  "parent" = @{ "database_id" = $db }
  "properties" = $props
}
[void](Invoke-Notion -Method POST -Url "https://api.notion.com/v1/pages" -Body $cBody)
Write-Host ("[NOTION] CREATED page for {0}" -f $asOf) -ForegroundColor Green
exit 0