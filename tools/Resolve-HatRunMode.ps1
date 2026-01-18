[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$m){
  Write-Host ("[FAIL-CLOSED] " + $m) -ForegroundColor Red
  exit 2
}

$raw = (($env:HAT_MODE + "")).Trim()
$u = $raw.ToUpperInvariant()

if($u -eq "PAPER_LIVE" -or $u -eq "PAPER-LIVE"){ $u = "PAPERLIVE" }

if(-not $u){
  # Ladder-1 dashboard must be runnable even when env is not pre-set.
  # Fail-closed semantics are preserved by marking source + warning.
  $u = "PAPERLIVE"
  $out = [ordered]@{
    run_mode     = $u
    is_live      = ($u -eq "LIVE")
    is_paper     = ($u -ne "LIVE")
    is_paperlive = ($u -eq "PAPERLIVE")
    mode_source  = "default_missing_env"
    warning      = "HAT_MODE missing; defaulting to PAPERLIVE"
  }
  $out | ConvertTo-Json -Depth 4
  exit 0
}
if($u -notin @("LIVE","PAPERLIVE","PAPER")){
  Fail ("invalid HAT_MODE=" + $raw + " (normalized=" + $u + ") expected LIVE | PAPERLIVE | PAPER")
}

$out = [ordered]@{
  run_mode     = $u
  is_live      = ($u -eq "LIVE")
  is_paper     = ($u -ne "LIVE")
  is_paperlive = ($u -eq "PAPERLIVE")
}
$out | ConvertTo-Json -Depth 4