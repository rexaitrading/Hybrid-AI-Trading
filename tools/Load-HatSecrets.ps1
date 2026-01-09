[CmdletBinding()]
param(
  [string]$RepoRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

function Fail([string]$m){ throw ("[SECRETS] FAIL-CLOSED: " + $m) }

$toolsDir = $PSScriptRoot
if(-not $toolsDir){ Fail "PSScriptRoot empty" }

# RepoRoot resolution order:
# 1) explicit -RepoRoot
# 2) env:HAT_REPO_ROOT
# 3) tools\Go-RepoRoot.ps1
if($RepoRoot){
  $RepoRoot = ($RepoRoot + "").Trim()
} elseif($env:HAT_REPO_ROOT){
  $RepoRoot = ($env:HAT_REPO_ROOT + "").Trim()
} else {
  $RepoRoot = & (Join-Path $toolsDir "Go-RepoRoot.ps1")
  $RepoRoot = ($RepoRoot + "").Trim()
}

if(-not $RepoRoot){ Fail "RepoRoot empty (arg/env/go-reporoot)" }
$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)
if(-not (Test-Path -LiteralPath $RepoRoot)){ Fail ("RepoRoot not found: " + $RepoRoot) }

$keysFile = Join-Path $RepoRoot ".secrets\hat_keys.env.cleaned"
if(-not (Test-Path -LiteralPath $keysFile)){ Fail ("Missing canonical keys file: " + $keysFile) }

# Load KEY=VALUE pairs into env (no echo of secrets)
$lines = @(Get-Content -LiteralPath $keysFile -Encoding utf8)
foreach($ln in $lines){
  $t = ($ln + "").Trim()
  if(-not $t){ continue }
  if($t.StartsWith("#")){ continue }
  if($t -match '^(?i)\s*export\s+'){ $t = ($t -replace '^(?i)\s*export\s+','').Trim() }
  if($t -notmatch '^[A-Za-z_][A-Za-z0-9_]*\s*='){ continue }

  $k = ($t.Split("=",2)[0]).Trim()
  $v = ($t.Split("=",2)[1]).Trim()

  if(($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'"))){
    if($v.Length -ge 2){ $v = $v.Substring(1,$v.Length-2) }
  }

  if($k){ Set-Item -Path ("Env:" + $k) -Value $v }
}

# Canonical aliases (legacy)
if($env:POLYGON_API_KEY){ $env:POLYGON_KEY = $env:POLYGON_API_KEY }
if($env:ALPACA_API_KEY){
  $env:ALPACA_KEY    = $env:ALPACA_API_KEY
  $env:ALPACA_KEY_ID = $env:ALPACA_API_KEY
}
if($env:ALPACA_SECRET_KEY){ $env:ALPACA_SECRET = $env:ALPACA_SECRET_KEY }

function _IsBad([string]$v){
  if(-not $v){ return $true }
  $t = $v.Trim()
  return ($t -match '<' -or $t -match '(?i)placeholder' -or $t -match '(?i)your' -or $t.Length -lt 16)
}
function _GetEnv([string]$name){
  $it = Get-Item -Path ("Env:" + $name) -ErrorAction SilentlyContinue
  if($it){ return ($it.Value + "") }
  return ""
}

foreach($rk in @("POLYGON_API_KEY","ALPACA_API_KEY","ALPACA_SECRET_KEY")){
  $v = _GetEnv $rk
  if(_IsBad $v){ Fail ($rk + " missing/placeholder") }
}

Write-Host "[SECRETS] Loaded canonical keys (cleaned)" -ForegroundColor Green