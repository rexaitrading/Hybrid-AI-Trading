[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)]
  [string]$BlockGPath = ".\logs\blockg_status_stub.json",

  [Parameter(Mandatory=$false)]
  [string]$OutPath = ".\logs\nvda_live_ready_stamp.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

function Write-Utf8NoBom {
  param([string]$Path, [string]$Text)

  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)

  # IMPORTANT: use a real string path (not PathInfo)
  $base = (Get-Location).Path

  # Support both relative and absolute OutPath
  $full = if ([System.IO.Path]::IsPathRooted($Path)) { $Path } else { Join-Path $base $Path }

  # Ensure parent directory exists
  $parent = Split-Path -Parent $full
  if ($parent -and (-not (Test-Path -LiteralPath $parent))) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
  }

  [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}$today = (Get-Date).Date
$isWeekend = ((Get-Date).DayOfWeek -in @("Saturday","Sunday"))
if ($isWeekend) { $reasons.Add("weekend_not_arming_live"); $nvdaLiveReady = $false }

$nvdaBlockgReady = $false
$reasons = New-Object System.Collections.Generic.List[string]

if (-not (Test-Path -LiteralPath $BlockGPath)) {
  $reasons.Add("missing_blockg_status_stub")
} else {
  try {
    $j = Get-Content $BlockGPath -Raw -Encoding utf8 | ConvertFrom-Json
    if ($null -ne $j.nvda_blockg_ready) {
      $nvdaBlockgReady = [bool]$j.nvda_blockg_ready
    } else {
      $reasons.Add("blockg_missing_nvda_blockg_ready")
    }
  } catch {
    $reasons.Add("blockg_parse_error")
  }
}

# Fail-closed arming policy (tighten later if needed)
$nvdaLiveReady = $false
if (-not $nvdaBlockgReady) { $nvdaLiveReady = $false; $reasons.Add("nvda_blockg_not_ready") }
if ($isWeekend) { $nvdaLiveReady = $false; $reasons.Add("weekend_not_arming_live") }

# --- Allow arming only when conditions are explicitly satisfied (fail-closed) ---
if ($nvdaBlockgReady -and (-not $isWeekend)) {
  $nvdaLiveReady = $true
}
if ($isWeekend) { $reasons.Add("weekend_not_arming_live") }
# Premarket authoritative veto (fail-closed)
$premarketRc = $env:HAT_PREMARKET_RC
if ([string]::IsNullOrWhiteSpace($premarketRc)) {
  $nvdaLiveReady = $false
  $reasons.Add("missing_premarket_rc_env")
} elseif ($premarketRc -ne "0") {
  $nvdaLiveReady = $false
  $reasons.Add("premarket_rc_not_zero=" + $premarketRc)
}
$payload = [ordered]@{
  ts_utc         = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date     = $today.ToString("yyyy-MM-dd")
  nvda_live_ready = $nvdaLiveReady
  nvda_blockg_ready = $nvdaBlockgReady
  reasons        = $reasons
}

$json = ($payload | ConvertTo-Json -Depth 6)
Write-Utf8NoBom -Path $OutPath -Text $json

if ($nvdaLiveReady) {
  Write-Host "[NVDA-STAMP] READY wrote $OutPath" -ForegroundColor Green
  exit 0
} else {
  Write-Host "[NVDA-STAMP] NOT_READY wrote $OutPath reasons=$($reasons -join ';')" -ForegroundColor Yellow
  exit 2
}
