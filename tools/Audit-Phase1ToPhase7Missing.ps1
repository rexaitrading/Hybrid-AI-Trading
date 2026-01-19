[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-RepoRoot {
  $root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
  if(-not (Test-Path -LiteralPath (Join-Path $root ".git"))){
    throw "[FAIL-CLOSED] repo root .git not found: " + $root
  }
  return $root
}

$repoRoot = Resolve-RepoRoot
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

$outMd   = Join-Path $repoRoot "logs\audit_phase1_to_phase7_missing.md"
$outJson = Join-Path $repoRoot "logs\audit_phase1_to_phase7_missing.json"
New-Item -ItemType Directory -Force -Path (Join-Path $repoRoot "logs") | Out-Null

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outMd, "", $utf8NoBom)

function W([string]$s){
  [System.IO.File]::AppendAllText($outMd, ($s + "`n"), $utf8NoBom)
}

$global:__J = [ordered]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  items  = @()
}

function JAdd([hashtable]$h){
  $global:__J.items += @([pscustomobject]$h)
}

function Get-PropNames($obj){
  try {
    if($null -eq $obj){ return @() }
    return @($obj.PSObject.Properties.Name)
  } catch { return @() }
}

function Get-StringProp($obj,[string]$name,[string]$default=""){
  try {
    if($null -eq $obj){ return $default }
    $p = Get-PropNames $obj
    if($p -contains $name){ return ("" + $obj.$name) }
    return $default
  } catch { return $default }
}

function Get-BoolProp($obj,[string]$name,[bool]$default=$false){
  try {
    if($null -eq $obj){ return $default }
    $p = Get-PropNames $obj
    if($p -contains $name){ return [bool]$obj.$name }
    return $default
  } catch { return $default }
}

W "# Phase-1 to Phase-7 Audit (Missing + Upgrade Opportunities)"
W ""
W ("- Generated: {0}" -f (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"))
W ""

# A) Git / Workspace Hygiene
W "## A) Git / Workspace Hygiene"
$st = @(git status --porcelain)

if($st.Count -eq 0){
  W "- OK Clean working tree"
  JAdd @{ area="git"; check="status_clean"; ok=$true; detail="" }
} else {
  $stLines = @(); for($j=0; $j -lt $st.Count; $j++){ $stLines += @("" + $st[$j]) }
  W "- WARN Uncommitted/untracked present"
  W "```"
  for($j=0; $j -lt $stLines.Count; $j++){ W ("" + $stLines[$j]) }
  W "```"
  JAdd @{ area="git"; check="status_clean"; ok=$false; detail=($stLines -join "`n") }

  $untracked = @(); for($j=0; $j -lt $stLines.Count; $j++){ $u = ("" + $stLines[$j]); if($u -match '^\?\?'){ $untracked += @($u) } }
  if($untracked.Count -gt 0){
    W "- WARN Untracked files:"
    foreach($u0 in $untracked){ W ("  - " + ($u0 + "")) }
    JAdd @{ area="git"; check="untracked_present"; ok=$false; detail=($untracked -join "`n") }
  } else {
    JAdd @{ area="git"; check="untracked_present"; ok=$true; detail="" }
  }
}

# B) Block-G Contract (Authoritative)
W ""
W "## B) Block-G Contract (Authoritative)"

$canonMkts = @("US","JP","HK","HK_SH","HK_SZ","SG","IN","KR","TW")

foreach($m0 in $canonMkts){
  $mU = ("" + $m0).ToUpperInvariant().Trim()
  $mRun = $mU; if($mRun -eq "HK_SH" -or $mRun -eq "HK_SZ"){ $mRun = "HK" }
  if(-not $mU){ $mU = "US" }

  W ""
  W ("### Market {0}" -f $mU)

  $bgOut = powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Build-BlockGStatusStub.ps1") -Market $mRun -Symbol ALL 2>&1
  $bgExit = $LASTEXITCODE
  W ("- Build-BlockGStatusStub exit={0}" -f $bgExit)
  JAdd @{ area="blockg"; check=("builder_exit0_" + $mU); ok=($bgExit -eq 0); detail=($bgOut | Out-String) }

  $cp = Join-Path (Join-Path (Join-Path $repoRoot "logs") $mU) "blockg_status_stub.json"
  if(Test-Path -LiteralPath $cp){
    $stj = Get-Content -LiteralPath $cp -Raw -Encoding UTF8 | ConvertFrom-Json

    $nv = Get-BoolProp $stj "nvda_blockg_ready" $false
    W ("- nvda_blockg_ready={0}" -f $nv)

    # Reasons (schema-safe): only read fields that actually exist
    $reasons = @()
    $csr = (Get-StringProp $stj "contract_semantics_reason" "").Trim()
    if($csr){ $reasons += @("contract_semantics_reason=" + $csr) }
    $rr = (Get-StringProp $stj "regime_reason" "").Trim()
    if($rr){ $reasons += @("regime_reason=" + $rr) }
    $rar = (Get-StringProp $stj "regime_actions_reason" "").Trim()
    if($rar){ $reasons += @("regime_actions_reason=" + $rar) }

    if($reasons.Count -gt 0){
      W "- reasons:"
      foreach($r0 in $reasons){ W ("  - " + ($r0 + "")) }
    }

    JAdd @{ area="blockg"; check=("nvda_ready_" + $mU); ok=$nv; detail=(@($reasons) -join "; ") }
  } else {
    W ("- MISSING {0}" -f $cp)
    JAdd @{ area="blockg"; check=("contract_exists_" + $mU); ok=$false; detail=$cp }
  }
}

# Write JSON summary
$jtxt = ($global:__J | ConvertTo-Json -Depth 8)
[System.IO.File]::WriteAllText($outJson, ($jtxt -replace "`r`n","`n") + "`n", $utf8NoBom)

W ""
W "---"
W "Generated files:"
W ("- {0}" -f $outMd)
W ("- {0}" -f $outJson)

("OK wrote:`n" + ($outMd + "") + "`n" + ($outJson + "")) | Out-Host
