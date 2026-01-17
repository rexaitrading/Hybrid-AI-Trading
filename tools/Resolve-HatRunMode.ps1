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
  Fail "missing HAT_MODE (expected LIVE | PAPERLIVE | PAPER)"
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
