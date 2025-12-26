[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)]
  [string]$DatabaseIdEnv,

  [int]$TimeoutSec = 15
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Utf8NoBom {
  param([string]$Path,[string]$Text)
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText((Resolve-Path $Path).Path, $Text, $utf8NoBom)
}

$tok = [System.Environment]::GetEnvironmentVariable("NOTION_TOKEN","User")
if (-not $tok) { throw "NOTION_TOKEN is not set (User scope)." }

$db  = [System.Environment]::GetEnvironmentVariable($DatabaseIdEnv,"User")
if (-not $db)  { throw "$DatabaseIdEnv is not set (User scope)." }

$headers = @{
  Authorization    = "Bearer $tok"
  "Notion-Version" = "2022-06-28"
  "Content-Type"   = "application/json"
}

$uri = "https://api.notion.com/v1/databases/$db"

try {
  $resp = Invoke-RestMethod -Method GET -Uri $uri -Headers $headers -TimeoutSec $TimeoutSec
} catch {
  # Preserve Notion error body for debugging
  $msg = $_.Exception.Message
  throw "NOTION PRECHECK FAIL: cannot GET database via integration. env=$DatabaseIdEnv db=$db :: $msg"
}

if ($resp.object -ne "database") {
  throw "NOTION PRECHECK FAIL: unexpected response object=$($resp.object)"
}

Write-Host ("NOTION_PRECHECK_OK env={0} db={1} title={2}" -f $DatabaseIdEnv, $db, (($resp.title | Select-Object -First 1).plain_text)) -ForegroundColor Green
exit 0