[CmdletBinding()]
param(
  [string]$StatusPath = ".\logs\blockg_status_stub.json",
  [string]$OutPath    = ".\logs\nvda_live_ready_stamp.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Utf8NoBom {
  param([string]$Path,[string]$Text)

  $enc = New-Object System.Text.UTF8Encoding($false)

  # repo root = tools\.. (deterministic)
  $repoRoot = Split-Path -Parent $PSScriptRoot

  $full = $Path
  if(-not [System.IO.Path]::IsPathRooted($full)){
    $full = Join-Path $repoRoot $Path
  }

  $t = ($Text -replace "`r`n","`n")
  if(-not $t.EndsWith("`n")){ $t += "`n" }

  $dir = Split-Path -Parent $full
  if($dir -and -not (Test-Path $dir)){ New-Item -ItemType Directory -Force -Path $dir | Out-Null }

  [System.IO.File]::WriteAllText($full, $t, $enc)
}

if(-not (Test-Path $StatusPath)){
  $out = [ordered]@{
    ts_utc     = (Get-Date).ToUniversalTime().ToString("o")
    as_of_date = (Get-Date).ToString("yyyy-MM-dd")
    nvda_live_ready = $false
    reason = "missing_blockg_status"
  } | ConvertTo-Json -Depth 8
  Write-Utf8NoBom -Path $OutPath -Text $out
  exit 2
}

$raw = Get-Content -LiteralPath $StatusPath -Raw -Encoding utf8
$st  = $raw | ConvertFrom-Json

$today = (($st.as_of_date) + "").Trim()
if(-not $today){ $today = (Get-Date).ToString("yyyy-MM-dd") }
$okDate = (($st.as_of_date + "") -eq $today)

$ready = [bool]($st.nvda_blockg_ready) -and $okDate

$out = [ordered]@{
  ts_utc     = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date = $today
  nvda_live_ready = $ready
  blockg_as_of_date = ($st.as_of_date + "")
  phase4_ok_today = [bool]($st.phase4_ok_today)
  ev_hard_daily_ok_today = [bool]($st.ev_hard_daily_ok_today)
  gatescore_ok_today = [bool]($st.gatescore_ok_today)
  reasons_not_ready = @($st.reasons_not_ready)
} | ConvertTo-Json -Depth 10

Write-Utf8NoBom -Path $OutPath -Text $out

if(-not $ready){ exit 2 }
exit 0
