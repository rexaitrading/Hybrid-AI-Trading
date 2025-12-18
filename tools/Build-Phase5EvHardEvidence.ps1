[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)][string]$AsOf = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Resolve-RepoRoot {
  $scriptPath = $PSCommandPath
  if([string]::IsNullOrWhiteSpace($scriptPath)){ $scriptPath = $MyInvocation.MyCommand.Path }
  if([string]::IsNullOrWhiteSpace($scriptPath)){ throw "[EV-HARD-EVIDENCE] cannot resolve script path" }

  $d = Split-Path -Parent $scriptPath
  while($true){
    if(Test-Path -LiteralPath (Join-Path $d ".git")){ return $d }
    $p = Split-Path -Parent $d
    if([string]::IsNullOrWhiteSpace($p) -or $p -eq $d){ break }
    $d = $p
  }
  throw "[EV-HARD-EVIDENCE] Could not find .git by walking up from $scriptPath"
}

$repoRoot = Resolve-RepoRoot
Set-Location $repoRoot

$logs = Join-Path $repoRoot "logs"
if(-not (Test-Path $logs)){ New-Item -ItemType Directory -Force -Path $logs | Out-Null }

$today = if($AsOf){ $AsOf } else { (Get-Date).ToString("yyyy-MM-dd") }

$snapPath = Join-Path $logs "phase5_ev_hard_veto_snapshot.json"
$outPath  = Join-Path $logs "phase5_ev_hard_veto_evidence.json"

# fail-closed defaults
$ok = $false
$reason = "missing_phase5_ev_hard_veto_snapshot"

if(Test-Path $snapPath){
  try {
    $raw = Get-Content $snapPath -Raw -Encoding utf8
    if ($raw.Length -gt 0 -and [int][char]$raw[0] -eq 65279) { $raw = $raw.TrimStart([char]65279) }
    $o = $raw | ConvertFrom-Json -ErrorAction Stop

    $asOf = [string]$o.as_of_date
    if($asOf -ne $today){
      $ok = $false
      $reason = "snapshot_stale"
    } else {
      $ok = [bool]$o.ok
      $reason = if($ok){"snapshot_ok"}else{"snapshot_not_ok"}
      if($o.PSObject.Properties.Name -contains "reason" -and $o.reason){ $reason = [string]$o.reason }
    }
  } catch {
    $ok = $false
    $reason = "snapshot_parse_failed"
  }
}

$payload = [ordered]@{
  ts_utc   = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date = $today
  ok       = $ok
  reason   = $reason
  inputs   = [ordered]@{
    source = "phase5_ev_hard_veto_snapshot.json"
  }
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$jsonLf = (($payload | ConvertTo-Json -Depth 6) -replace "`r`n","`n") + "`n"
[IO.File]::WriteAllText($outPath, $jsonLf, $utf8NoBom)

Write-Host "[EV-HARD-EVIDENCE] wrote $outPath ok=$ok reason=$reason" -ForegroundColor Green
exit 0