[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)]
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market
)

# --- Stock Connect market ID normalization (NO engine constraints; logs MUST match Resolve-RunContext) ---
$marketIn = ($Market + "").Trim().ToUpperInvariant()
switch($marketIn){
default { }
}
# --- end normalization ---

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Find-RepoRoot([string]$start){
  if(-not $start){ throw "[FAIL-CLOSED] Find-RepoRoot start path is empty." }
  $p = (Resolve-Path -LiteralPath $start).Path
  while($true){
    if(Test-Path -LiteralPath (Join-Path $p ".git")){ return $p }
    $parent = Split-Path -Parent $p
    if(-not $parent -or $parent -eq $p){ break }
    $p = $parent
  }
  throw "[FAIL-CLOSED] RepoRoot not found (walk-up to .git failed) start=$start"
}

# Canonical repo root from this script's folder (never trust env vars / configs for path)
$repoRoot = Find-RepoRoot $PSScriptRoot

$m = ([string]$Market).ToUpperInvariant().Trim()
if(-not $m){ throw "[FAIL-CLOSED] Market empty" }

$logRoot = Join-Path (Join-Path $repoRoot "logs") $m
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

# Emit ONLY the path (no extra Write-Host)
$logRoot
