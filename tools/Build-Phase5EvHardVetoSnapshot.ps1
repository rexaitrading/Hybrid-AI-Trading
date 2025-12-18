[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)][string]$AsOf = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Resolve-RepoRoot {
  $rootFile = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.hat\repo_root.txt"))
  if(Test-Path -LiteralPath $rootFile){
    $s = (Get-Content -LiteralPath $rootFile -Raw -Encoding UTF8)
    if ($s.Length -gt 0 -and [int][char]$s[0] -eq 65279) { $s = $s.TrimStart([char]65279) }
    $pp = $s.Trim()
    if($pp){
      $full = [System.IO.Path]::GetFullPath($pp)
      if(Test-Path -LiteralPath (Join-Path $full ".git")){ return $full }
      throw "[REPOROOT] .hat/repo_root.txt points to missing repo: $full"
    }
  }
  throw "[REPOROOT] Missing .hat/repo_root.txt (fail-closed)"
}

$repoRoot = Resolve-RepoRoot
Set-Location $repoRoot

$logs = Join-Path $repoRoot "logs"
if(-not (Test-Path $logs)){ New-Item -ItemType Directory -Force -Path $logs | Out-Null }

$today = if($AsOf){ $AsOf } else { (Get-Date).ToString("yyyy-MM-dd") }
$out   = Join-Path $logs "phase5_ev_hard_veto_snapshot.json"

# AUTHORITATIVE MANUAL INPUT (tracked, ASCII-safe)
$inPath = Join-Path $repoRoot ".hat\inputs\phase5_ev_hard_veto_snapshot_input.json"

$ok = $false
$reason = "missing_snapshot_input"

if(Test-Path -LiteralPath $inPath){
  try {
    $j = Get-Content -LiteralPath $inPath -Raw -Encoding UTF8
    if ($j.Length -gt 0 -and [int][char]$j[0] -eq 65279) { $j = $j.TrimStart([char]65279) }
    $o = $j | ConvertFrom-Json -ErrorAction Stop

    $as = [string]$o.as_of_date
    if($as -ne $today){
      $ok = $false
      $reason = "snapshot_input_stale"
    } else {
      $ok = [bool]$o.ok
      if($o.PSObject.Properties.Name -contains "reason" -and $o.reason){
        $reason = [string]$o.reason
      } else {
        $reason = if($ok){"manual_ok"}else{"manual_not_ok"}
      }
    }
  } catch {
    $ok = $false
    $reason = "snapshot_input_parse_failed"
  }
}

$payload = [ordered]@{
  ts_utc    = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date= $today
  ok        = $ok
  reason    = $reason
  inputs    = [ordered]@{
    input = ".hat/inputs/phase5_ev_hard_veto_snapshot_input.json"
  }
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$jsonLf = (($payload | ConvertTo-Json -Depth 6) -replace "`r`n","`n") + "`n"
[IO.File]::WriteAllText($out, $jsonLf, $utf8NoBom)

Write-Host "[EV-HARD-VETO-SNAPSHOT] wrote $out ok=$ok reason=$reason" -ForegroundColor Green
exit 0