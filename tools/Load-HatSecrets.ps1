[CmdletBinding()]
param(
  [string]$VaultPath = ".secrets\hat_keys.env"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path ".").Path
$p = Join-Path $repoRoot $VaultPath
if(-not (Test-Path -LiteralPath $p)){ throw "Missing vault file: $p" }

$lines = Get-Content $p -Encoding utf8
$set = 0

foreach($ln in $lines){
  $t = ($ln + "").Trim()
  if(-not $t) { continue }
  if($t.StartsWith("#")) { continue }
  if($t -notmatch "^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$"){ continue }

  $k = $matches[1]
  $v = $matches[2]

  # strip optional quotes
  if($v.Length -ge 2 -and (($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'")))){
    $v = $v.Substring(1, $v.Length-2)
  }

  Set-Item -Path ("Env:{0}" -f $k) -Value $v
  $set++
}

Write-Host ("[SECRETS] loaded {0} keys from {1}" -f $set, $VaultPath) -ForegroundColor Green
exit 0