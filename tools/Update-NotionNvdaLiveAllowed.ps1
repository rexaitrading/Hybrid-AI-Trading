[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$tools = Split-Path -Parent $PSCommandPath

# 1) Fail-closed Notion visibility check
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $tools "Test-NotionDbVisible.ps1") -DatabaseIdEnv NOTION_DB_DAYS_NVDA_LIVE_ALLOWED

# 2) Build payload (json)
$p1 = Join-Path $tools "Build-NotionNvdaLiveAllowedPayload.ps1"
$payload = powershell -NoProfile -ExecutionPolicy Bypass -File $p1
if (-not $payload) { throw "Build payload returned empty output." }

# 3) Push payload
$p2 = Join-Path $tools "Push-NotionNvdaLiveAllowed.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File $p2