[CmdletBinding()]
param(
  [string]$EvidencePath = ".\logs\ev_hard_evidence_raw.json",
  [string]$OutPath = ".\logs\phase5_ev_hard_veto_snapshot.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function As-Bool([object]$v) {
  if ($null -eq $v) { return $false }
  if ($v -is [bool]) { return [bool]$v }
  $s = ("" + $v).Trim()
  return ($s -in @("1","true","True","TRUE","yes","YES"))
}

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

$today = (Get-Date).ToString("yyyy-MM-dd")
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")

$ok = $false
$reason = "evidence_missing_failclosed"

if (Test-Path $EvidencePath) {
  $raw = Get-Content $EvidencePath -Raw
  $j = $null
  try { $j = $raw | ConvertFrom-Json } catch { $j = $null }

  if ($null -eq $j) {
    $ok = $false
    $reason = "evidence_parse_error_failclosed"
  } else {
    # require evidence to be for today
    $asOf = (($j.as_of_date) + "").Trim()
    if ($asOf -ne $today) {
      $ok = $false
      $reason = ("evidence_stale_failclosed as_of_date={0} today={1}" -f $asOf,$today)
    } else {
      # if evidence itself declares ok=true, accept; otherwise fail
      $ok = As-Bool $j.ok
      $reason = if($ok){"computed_from_evidence_ok"}else{"computed_from_evidence_not_ok"}
    }
  }
} else {
  $ok = $false
  $reason = ("evidence_missing_failclosed path={0}" -f $EvidencePath)
}

$out = [ordered]@{
  ts_utc = $tsUtc
  as_of_date = $today
  ok = $ok
  reason = $reason
} | ConvertTo-Json -Depth 6

Write-Utf8NoBom -Path $OutPath -Text ($out + "`n")
Write-Host ("[EV-HARD-SNAPSHOT] wrote {0} ok={1} reason={2}" -f $OutPath,$ok,$reason) -ForegroundColor Cyan
exit 0
