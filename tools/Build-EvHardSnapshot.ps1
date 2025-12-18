[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)][string]$AsOf = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$logs = Join-Path $repoRoot "logs"
if(-not (Test-Path $logs)){ New-Item -ItemType Directory -Force -Path $logs | Out-Null }

$today = if($AsOf){ $AsOf } else { (Get-Date).ToString("yyyy-MM-dd") }
$out   = Join-Path $logs "ev_hard_snapshot.json"

# REAL evidence hook (replace later with your real EV-hard veto file)
# For now we fail-closed unless a file exists proving EV-hard passed today.
$evidence = Join-Path $logs "phase5_ev_hard_veto_evidence.json"

$ok = $false
$reason = "missing_evidence"

if(Test-Path $evidence){
  try {
    $raw = Get-Content $evidence -Raw -Encoding utf8
    if ($raw.Length -gt 0 -and [int][char]$raw[0] -eq 65279) { $raw = $raw.TrimStart([char]65279) }
    $o = $raw | ConvertFrom-Json -ErrorAction Stop
    if([string]$o.as_of_date -eq $today -and [bool]$o.ok -eq $true){
      $ok = $true
      $reason = "computed_from_evidence"
    } else {
      $ok = $false
      $reason = "evidence_not_ok_or_stale"
    }
  } catch {
    $ok = $false
    $reason = "evidence_parse_failed"
  }
}

$payload = [ordered]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date = $today
  ok = $ok
  reason = $reason
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($out, (($payload | ConvertTo-Json -Depth 4) -replace "`r`n","`n") + "`n", $utf8NoBom)

Write-Host "[EV-HARD-SNAP] wrote $out ok=$ok reason=$reason" -ForegroundColor Green
exit 0