[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- HAT_KEYS_SOURCE_BEGIN (canonical) ---
$toolsDir = $PSScriptRoot
if(-not $toolsDir){ throw "[SECRETS] FAIL-CLOSED: PSScriptRoot empty (unexpected)" }

$repoRoot = & (Join-Path $toolsDir "Go-RepoRoot.ps1")
if(-not $repoRoot){ throw "[SECRETS] FAIL-CLOSED: Go-RepoRoot.ps1 returned empty repoRoot" }
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)

$keysFile = Join-Path $repoRoot ".secrets\hat_keys.env.cleaned"
if(-not (Test-Path -LiteralPath $keysFile)){ throw ("[SECRETS] Missing canonical keys file: " + $keysFile) }

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

  if($k){
    Set-Item -Path ("Env:" + $k) -Value $v
  }
}

# Canonical aliases (legacy compatibility, forced to canonical)
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
  if(_IsBad $v){ throw ("[SECRETS] FAIL-CLOSED: " + $rk + " missing/placeholder") }
}

Write-Host ("[SECRETS] Loaded canonical keys from " + $keysFile) -ForegroundColor Green
# --- HAT_KEYS_SOURCE_END ---