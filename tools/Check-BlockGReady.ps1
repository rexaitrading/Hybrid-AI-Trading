[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("NVDA","SPY","QQQ","ALL")]
    [string]$Symbol = "NVDA",

    [Parameter(Mandatory = $false)]
    [switch]$UpdateNotion,

    [Parameter(Mandatory = $false)]
    [switch]$RequireNotionRow
)

# ALL_MODE_BLOCKGREADY
if($Symbol -eq "ALL"){
  foreach($s in @("NVDA","SPY","QQQ")){
    & $PSCommandPath -Symbol $s
    if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
  }
  exit 0
}

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail-Contract([string]$Msg){
  [Console]::Error.WriteLine($Msg)
  exit 2
}

function Fail-Script([string]$Msg){
  [Console]::Error.WriteLine($Msg)
  exit 1
}

# --- Notion integration helpers (clean; no backticks) ---
function Invoke-NotionDbQueryToday {
  param(
    [Parameter(Mandatory=$true)][string]$DbIdEnv,
    [Parameter(Mandatory=$true)][string]$DatePropName,
    [Parameter(Mandatory=$true)][string]$Today
  )

  $tok = [System.Environment]::GetEnvironmentVariable("NOTION_TOKEN","User")
  if (-not $tok) { Fail-Contract "BLOCK-G: NOTION_TOKEN not set (User scope)." }

  $db = [System.Environment]::GetEnvironmentVariable($DbIdEnv,"User")
  if (-not $db) { Fail-Contract "BLOCK-G: $DbIdEnv not set (User scope)." }

  $headers = @{
    Authorization    = "Bearer $tok"
    "Notion-Version" = "2022-06-28"
    "Content-Type"   = "application/json"
  }

  $qBody = @{
    filter = @{
      property = $DatePropName
      date     = @{ equals = $Today }
    }
    page_size = 10
  }

  try {
    $uri  = ("https://api.notion.com/v1/databases/{0}/query" -f $db)
    $body = ($qBody | ConvertTo-Json -Depth 10)
    return Invoke-RestMethod -Method POST -Uri $uri -Headers $headers -Body $body
  } catch {
    Fail-Contract ("BLOCK-G: Notion query failed (db_env={0}) :: {1}" -f $DbIdEnv, $_.Exception.Message)
  }
}

function Require-NotionNvdaLiveAllowedToday {
  param([Parameter(Mandatory=$true)][string]$Today)

  $r = Invoke-NotionDbQueryToday -DbIdEnv "NOTION_DB_DAYS_NVDA_LIVE_ALLOWED" -DatePropName "date" -Today $Today
  if (-not $r -or -not $r.results) { Fail-Contract "BLOCK-G: Notion has no results object for today=$Today." }

  $ok = $false
  foreach($page in @($r.results)){
    $props = $page.properties
    if ($props -and $props."NVDA Live Allowed" -and $props."NVDA Live Allowed".checkbox -eq $true) {
      $ok = $true; break
    }
  }
  if (-not $ok) { Fail-Contract "BLOCK-G: Notion does not show NVDA Live Allowed=TRUE for today=$Today." }
}

function Invoke-UpdateNotionNvdaLiveAllowed {
  param([Parameter(Mandatory=$true)][string]$ToolsDir)

  $u = Join-Path $ToolsDir "Update-NotionNvdaLiveAllowed.ps1"
  if (-not (Test-Path $u)) { Fail-Script "BLOCK-G: UpdateNotion requested but missing $u" }
  powershell -NoProfile -ExecutionPolicy Bypass -File $u
  if ($LASTEXITCODE -ne 0) { Fail-Script "BLOCK-G: UpdateNotion failed (exit=$LASTEXITCODE)." }
}

function Get-AsOfDateString {
  param([Parameter(Mandatory = $true)]$Payload)

  $props = $Payload.PSObject.Properties
  foreach ($name in @("as_of_date","date","trading_day")) {
    $prop = $props[$name]
    if ($prop -ne $null -and $prop.Value -ne $null -and $prop.Value -ne "") {
      $s = [string]$prop.Value
      return ($(if($s.Length -ge 10){ $s.Substring(0,10) } else { $s }))
    }
  }
  return $null
}

function To-StrictBool {
  param([Parameter(Mandatory = $true)]$Value)

  if ($null -eq $Value) { return $false }
  if ($Value -is [bool]) { return [bool]$Value }

  if ($Value -is [string]) {
    $v = $Value.Trim().ToLowerInvariant()
    if ($v -in @("1","true","yes","y"))  { return $true }
    if ($v -in @("0","false","no","n")) { return $false }
  }
  return [bool]$Value
}

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$logsStatus  = Join-Path $repoRoot "logs\blockg_status_stub.json"
$intelStatus = Join-Path $repoRoot ".intel\blockg_status_stub.json"

if (Test-Path $logsStatus) {
  $statusPath = $logsStatus
} elseif (Test-Path $intelStatus) {
  $statusPath = $intelStatus
} else {
  Fail-Contract "BLOCK-G: status JSON not found (.intel or logs)."
}

Write-Host "BLOCK-G: using status JSON at $statusPath" -ForegroundColor Cyan

try {
  $raw = Get-Content -Path $statusPath -Raw -Encoding UTF8
  $status = $raw | ConvertFrom-Json
} catch {
  Fail-Script "BLOCK-G: failed to parse status JSON at $statusPath."
}

$asOf = Get-AsOfDateString -Payload $status
if (-not $asOf) { Fail-Script "BLOCK-G: status JSON missing as_of_date/date/trading_day." }

$today = (Get-Date).ToString("yyyy-MM-dd")
if ($asOf -ne $today) { Fail-Contract "BLOCK-G: status JSON date mismatch. as_of_date=$asOf, today=$today." }

# Optional: enforce Notion row agreement (fail-closed)
if ($RequireNotionRow) {
  Require-NotionNvdaLiveAllowedToday -Today $today
}

$phase23Ok    = To-StrictBool $status.phase23_health_ok_today
$evHardOk     = To-StrictBool $status.ev_hard_daily_ok_today
$gsFresh      = To-StrictBool $status.gatescore_fresh_today
$phase4Ok     = To-StrictBool $status.phase4_ok_today
$gsSamplesOk  = To-StrictBool $status.gatescore_samples_ok
$gsThreshOk   = To-StrictBool $status.gatescore_threshold_ok_today

if (-not $phase4Ok)    { Fail-Contract "BLOCK-G: phase4_ok_today is FALSE." }
if (-not $gsSamplesOk) { Fail-Contract "BLOCK-G: gatescore_samples_ok is FALSE." }
if (-not $gsThreshOk)  { Fail-Contract "BLOCK-G: gatescore_threshold_ok_today is FALSE." }

# Optional (if present in payload, enforce; else ignore)
if ($status.PSObject.Properties.Name -contains "min_samples_ok_today") {
  $minSamplesOk = To-StrictBool $status.min_samples_ok_today
  if (-not $minSamplesOk) { Fail-Contract "BLOCK-G: min_samples_ok_today is FALSE." }
}

if (-not $phase23Ok) { Fail-Contract "BLOCK-G: phase23_health_ok_today is FALSE." }
if (-not $evHardOk)  { Fail-Contract "BLOCK-G: ev_hard_daily_ok_today is FALSE." }
if (-not $gsFresh)   { Fail-Contract "BLOCK-G: gatescore_fresh_today is FALSE." }

switch ($Symbol.ToUpperInvariant()) {
  "NVDA" { $readyFlag = $status.nvda_blockg_ready }
  "SPY"  { $readyFlag = $status.spy_blockg_ready }
  "QQQ"  { $readyFlag = $status.qqq_blockg_ready }
  default { Fail-Contract "BLOCK-G: unknown symbol '$Symbol' for Block-G check." }
}

if (-not (To-StrictBool $readyFlag)) { Fail-Contract "BLOCK-G: per-symbol ready flag is FALSE for $Symbol." }

# Optional: update Notion (side-effect) AFTER contract checks pass
if ($UpdateNotion) {
  Invoke-UpdateNotionNvdaLiveAllowed -ToolsDir $toolsDir
}

Write-Host "BLOCK-G: READY for symbol=$Symbol (date=$asOf)." -ForegroundColor Green
exit 0