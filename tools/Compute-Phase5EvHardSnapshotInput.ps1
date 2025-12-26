[CmdletBinding()]
param(
  [string]$EvidencePath = ".\logs\ev_hard_snapshot.json",
  [string]$OutPath = ".\.hat\inputs\phase5_ev_hard_veto_snapshot_input.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Utf8NoBom([string]$Path, [string]$Text) {
  $enc = New-Object System.Text.UTF8Encoding($false)
  $full = $Path
  if (-not [System.IO.Path]::IsPathRooted($full)) {
    $repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
    $full = Join-Path $repoRoot $Path
  }
  $dir = Split-Path -Parent $full
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  [System.IO.File]::WriteAllText($full, $Text, $enc)
}

function Sha256Hex([string]$Text) {
  $sha = [System.Security.Cryptography.SHA256]::Create()
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
  $hash = $sha.ComputeHash($bytes)
  ($hash | ForEach-Object { $_.ToString("x2") }) -join ""
}

$today = (Get-Date).ToString("yyyy-MM-dd")

$computedPass = $false
$computedReason = "evidence_missing_failclosed"
$inputsHash = ""

if (Test-Path $EvidencePath) {
  $raw = Get-Content $EvidencePath -Raw
  $inputsHash = Sha256Hex $raw

  $j = $null
  try { $j = $raw | ConvertFrom-Json } catch { $j = $null }

  if ($null -eq $j) {
    $computedPass = $false
    $computedReason = "evidence_parse_error_failclosed"
  } else {
    $asOf = (($j.as_of_date) + "").Trim()
    $ok = $false
    try { $ok = [bool]$j.ok } catch { $ok = $false }

    if (-not $asOf) {
      $computedPass = $false
      $computedReason = "evidence_missing_as_of_date_failclosed"
    } elseif ($asOf -ne $today) {
      $computedPass = $false
      $computedReason = ("evidence_stale_failclosed as_of_date={0} today={1}" -f $asOf,$today)
    } elseif ($ok) {
      $computedPass = $true
      $computedReason = "computed_from_ev_hard_snapshot_ok"
    } else {
      $computedPass = $false
      $snapReason = ""
      try { $snapReason = (($j.reason) + "").Trim() } catch { $snapReason = "" }
      if ($snapReason) {
        $computedReason = "ev_hard_snapshot_not_ok: " + $snapReason
      } else {
        $computedReason = "computed_from_ev_hard_snapshot_not_ok"
      }
    }
  }
} else {
  $computedPass = $false
  $computedReason = ("evidence_missing_failclosed path={0}" -f $EvidencePath)
}

$payload = [ordered]@{
  as_of_date = $today
  ev_hard_veto_live_enabled = $true
  computed_pass = $computedPass
  computed_reason = $computedReason
  model_version = "v1"
  inputs_hash = $inputsHash
} | ConvertTo-Json -Depth 6

Write-Utf8NoBom -Path $OutPath -Text ($payload + "`n")
Write-Host ("[EV-HARD-COMPUTE] wrote {0} computed_pass={1} reason={2}" -f $OutPath,$computedPass,$computedReason) -ForegroundColor Cyan
exit 0
