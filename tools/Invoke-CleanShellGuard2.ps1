[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)]
  [string]$Tool,

  [string[]]$Args = @(),

  [hashtable]$EnvSet = @{} ,

  [string]$RepoRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Resolve-RepoRoot(){
  if((($RepoRoot + "")).Trim()){
    $r = [System.IO.Path]::GetFullPath((($RepoRoot + "")).Trim())
    if(-not (Test-Path -LiteralPath (Join-Path $r ".git"))){ throw "[FAIL-CLOSED] RepoRoot not a repo (.git missing): $r" }
    return $r
  }
  $toolsDir = Split-Path -Parent $PSCommandPath
  $rr = Split-Path -Parent $toolsDir
  $rr = [System.IO.Path]::GetFullPath($rr)
  if(-not (Test-Path -LiteralPath (Join-Path $rr ".git"))){ throw "[FAIL-CLOSED] script repo root invalid (.git missing): $rr" }
  return $rr
}

function Canon([string]$p){
  if(-not $p){ return "" }
  try { return (Resolve-Path -LiteralPath $p -ErrorAction Stop).Path } catch { return $p }
}

$rr = Resolve-RepoRoot
Set-Location -LiteralPath $rr
[System.Environment]::CurrentDirectory = $rr

# Resolve tool path
$toolPath = $Tool
if(-not [System.IO.Path]::IsPathRooted($toolPath)){
  $toolPath = Join-Path $rr $toolPath
}
$toolPath = Canon $toolPath
if(-not (Test-Path -LiteralPath $toolPath)){ throw "[FAIL-CLOSED] tool not found: $toolPath" }

# Build child script
$tmp = Join-Path $env:TEMP ("hat_guard2_" + (Get-Date).ToString("yyyyMMdd_HHmmss") + ".ps1")

$clearPins = @(
  "HAT_ASOF_DATE","HAT_AS_OF_DATE",
  "HAT_MARKET","HAT_SYMBOL","HAT_SESSION_NAME",
  "HAT_LOGS_DIR","HAT_LOGS_DIR_OUT",
  "HAT_MODE",
  "HAT_REPO_ROOT","HAT_IS_PAPER"
)

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add('$ErrorActionPreference="Stop"; Set-StrictMode -Version Latest; chcp 65001 | Out-Null')
$lines.Add(('Set-Location -LiteralPath "{0}"; [System.Environment]::CurrentDirectory="{0}"' -f $rr.Replace('"','""')))

foreach($k in $clearPins){
  $k2 = ([string]$k).Trim()
  if($k2){
    $lines.Add('try { Remove-Item -LiteralPath ("env:\' + $k2 + '") -Force -ErrorAction SilentlyContinue } catch { }')
  }
}

if($EnvSet -and $EnvSet.Count -gt 0){
  foreach($k in @($EnvSet.Keys)){
    $name = ([string]$k).Trim()
    if(-not $name){ continue }
    $val = $EnvSet[$k]
    if($val -eq $null){ continue }
    $v = ([string]$val).Replace('"','""')
    $lines.Add(('$env:{0} = "{1}"' -f $name, $v))
  }
}

# Direct-run tool (NO nested powershell)
$lines.Add(('$__tool = "{0}"' -f $toolPath.Replace('"','""')))
$lines.Add('$__args = @()')
if($Args -and $Args.Count -gt 0){
  foreach($a in $Args){
    $v = ("" + $a).Replace('"','""')
    $lines.Add(('$__args += "{0}"' -f $v))
  }
}
$lines.Add('& $__tool @__args *>&1 | Out-Host')
$lines.Add('exit $LASTEXITCODE')

$scriptText = ($lines -join "`n") -replace "`r`n","`n"
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($tmp, $scriptText, $utf8)

try {
  & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $tmp
  $code = $LASTEXITCODE
} finally {
  Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}

exit $code