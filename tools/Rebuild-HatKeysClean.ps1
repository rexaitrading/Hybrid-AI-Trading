[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$m){ throw "[KEYS] FAIL-CLOSED: $m" }

function IsPlaceholder([string]$v){
  if($null -eq $v){ return $true }
  $t = ($v + "").Trim()
  if(-not $t){ return $true }
  return ($t -match '<' -or $t -match '(?i)placeholder' -or $t -match '(?i)your' -or $t -match '(?i)changeme')
}
function Mask([string]$v){
  $t = ($v + "").Trim()
  if(-not $t){ return "<empty>" }
  if($t.Length -le 6){ return ("*" * $t.Length) }
  return ($t.Substring(0,3) + "..." + $t.Substring($t.Length-2,2))
}

$toolsDir = $PSScriptRoot
$repoRoot = & (Join-Path $toolsDir "Go-RepoRoot.ps1")
if(-not $repoRoot){ Fail "Go-RepoRoot.ps1 returned empty repoRoot" }
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)

$envPath = Join-Path $repoRoot ".secrets\hat_keys.env"
if(-not (Test-Path -LiteralPath $envPath)){ Fail "missing file: $envPath" }

$rawLines = @(Get-Content -LiteralPath $envPath -Encoding utf8)

$items = New-Object System.Collections.Generic.List[object]
for($i=0; $i -lt $rawLines.Count; $i++){
  $ln = ($rawLines[$i] + "")
  $t  = $ln.Trim()
  if(-not $t){ continue }
  if($t.StartsWith("#")){ continue }
  if($t -match '^(?i)\s*export\s+'){ $t = ($t -replace '^(?i)\s*export\s+','').Trim() }

  if($t -notmatch '^[A-Za-z_][A-Za-z0-9_]*\s*='){
    $items.Add([pscustomobject]@{key="__INVALID__"; value=$ln; line=($i+1)})
    continue
  }

  $k = ($t.Split("=",2)[0]).Trim()
  $v = ($t.Split("=",2)[1]).Trim()

  if(($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'"))){
    if($v.Length -ge 2){ $v = $v.Substring(1,$v.Length-2) }
  }

  $items.Add([pscustomobject]@{key=$k; value=$v; line=($i+1)})
}

$byKey = @($items | Where-Object {$_.key -ne "__INVALID__"} | Group-Object key)

$report = New-Object System.Collections.Generic.List[string]
$report.Add("[KEYS] RepoRoot=" + $repoRoot)
$report.Add("[KEYS] Input=" + $envPath)
$report.Add("[KEYS] ParsedKeys=" + (@($byKey).Count))

foreach($g in $byKey){
  $vals = @($g.Group | Select-Object -ExpandProperty value)
  $uniq = @($vals | Select-Object -Unique)
  if(@($uniq).Count -gt 1){
    $report.Add(("[DUPLICATE-CONFLICT] {0} has {1} distinct values at lines: {2}" -f $g.Name, @($uniq).Count, (($g.Group | Select-Object -ExpandProperty line) -join ",")))
    foreach($u in $uniq){
      $report.Add(("  - {0} = {1}" -f $g.Name, (Mask $u)))
    }
  } elseif($g.Count -gt 1){
    $report.Add(("[DUPLICATE] {0} repeated {1} times (same value), lines: {2}" -f $g.Name, $g.Count, (($g.Group | Select-Object -ExpandProperty line) -join ",")))
  }
}

function PickBest([string]$key){
  $g = $byKey | Where-Object Name -eq $key | Select-Object -First 1
  if(-not $g){ return $null }
  $vals = @($g.Group)
  $best = ($vals | Where-Object { -not (IsPlaceholder $_.value) } | Select-Object -Last 1)
  if($best){ return $best.value }
  return ($vals | Select-Object -Last 1).value
}

$canon = @{}
$canon["POLYGON_API_KEY"] = PickBest "POLYGON_API_KEY"
if(-not $canon["POLYGON_API_KEY"]){ $canon["POLYGON_API_KEY"] = PickBest "POLYGON_KEY" }
$canon["POLYGON_KEY"] = $canon["POLYGON_API_KEY"]

$canon["ALPACA_API_KEY"] = PickBest "ALPACA_API_KEY"
if(-not $canon["ALPACA_API_KEY"]){ $canon["ALPACA_API_KEY"] = PickBest "ALPACA_KEY" }
if(-not $canon["ALPACA_API_KEY"]){ $canon["ALPACA_API_KEY"] = PickBest "ALPACA_KEY_ID" }

$canon["ALPACA_SECRET_KEY"] = PickBest "ALPACA_SECRET_KEY"
if(-not $canon["ALPACA_SECRET_KEY"]){ $canon["ALPACA_SECRET_KEY"] = PickBest "ALPACA_SECRET" }

$canon["ALPACA_KEY"]    = $canon["ALPACA_API_KEY"]
$canon["ALPACA_KEY_ID"] = $canon["ALPACA_API_KEY"]
$canon["ALPACA_SECRET"] = $canon["ALPACA_SECRET_KEY"]

$canon["ALPACA_BASE_URL"] = PickBest "ALPACA_BASE_URL"
if(-not $canon["ALPACA_BASE_URL"]){ $canon["ALPACA_BASE_URL"] = "http://massive.com" }

$canon["BENZINGA_API_KEY"]   = PickBest "BENZINGA_API_KEY"
$canon["HAT_YT_CHANNEL_IDS"] = PickBest "HAT_YT_CHANNEL_IDS"

foreach($rk in @("POLYGON_API_KEY","ALPACA_API_KEY","ALPACA_SECRET_KEY")){
  $v = ($canon[$rk] + "")
  if(IsPlaceholder $v){
    $report.Add(("[FAIL] {0} is missing/placeholder => {1}" -f $rk, (Mask $v)))
    Fail "$rk is missing/placeholder in $envPath"
  }
}

$secretsDir = Join-Path $repoRoot ".secrets"
if(-not (Test-Path -LiteralPath $secretsDir)){ Fail "missing secrets dir: $secretsDir" }

$cleanFull = Join-Path $secretsDir "hat_keys.env.cleaned"
$repFull   = Join-Path $secretsDir "hat_keys.env.report.txt"

$outLines = New-Object System.Collections.Generic.List[string]
$outLines.Add("# Canonical HAT keys (generated) " + (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"))
$outLines.Add("# DO NOT commit secrets. Keep this file local.")
$outLines.Add("")

$order = @(
  "POLYGON_API_KEY","POLYGON_KEY",
  "ALPACA_BASE_URL",
  "ALPACA_API_KEY","ALPACA_SECRET_KEY","ALPACA_KEY","ALPACA_KEY_ID","ALPACA_SECRET",
  "BENZINGA_API_KEY",
  "HAT_YT_CHANNEL_IDS"
)

foreach($k in $order){
  if($canon.ContainsKey($k) -and ($null -ne $canon[$k])){
    $v = ($canon[$k] + "").Trim()
    if($v){
      if($v -match '\s'){ $outLines.Add("$k=`"$v`"") } else { $outLines.Add("$k=$v") }
    }
  }
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($cleanFull, (($outLines -join "`n") + "`n"), $utf8NoBom)

$report.Add("")
$report.Add("[CANON] (masked)")
foreach($k in $order){
  if($canon.ContainsKey($k)){
    $report.Add(("  {0} = {1}" -f $k, (Mask ($canon[$k] + ""))))
  }
}
[System.IO.File]::WriteAllText($repFull, (($report -join "`n") + "`n"), $utf8NoBom)

Write-Host ("[KEYS] OK: wrote " + $cleanFull) -ForegroundColor Green
Write-Host ("[KEYS] OK: wrote " + $repFull) -ForegroundColor Green