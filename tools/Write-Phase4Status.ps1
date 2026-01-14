[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ","CN_SH","CN_SZ")]
  [string]$Market = "",

  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Resolve-RepoRoot(){
  $envRoot = (($env:HAT_REPO_ROOT + "")).Trim()
  if($envRoot){
    try {
      $r = (Resolve-Path -LiteralPath $envRoot -ErrorAction Stop).Path
      if(Test-Path -LiteralPath (Join-Path $r ".git")){ return $r }
    } catch { }
  }
  $p = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..") -ErrorAction Stop).Path
  while($p -and -not (Test-Path -LiteralPath (Join-Path $p ".git"))){
    $parent = Split-Path -Parent $p
    if(-not $parent -or $parent -eq $p){ break }
    $p = $parent
  }
  if(-not $p -or -not (Test-Path -LiteralPath (Join-Path $p ".git"))){
    throw "[FAIL-CLOSED] repo root not found (.git missing). envRoot=$envRoot scriptRoot=$PSScriptRoot"
  }
  return $p
}
function Slice-Date([string]$d){
  if(-not $d){ return "" }
  $s = ([string]$d).Trim()
  if($s.Length -ge 10){ return $s.Substring(0,10) }
  return $s
}
function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  $Text = ($Text -replace "`r`n","`n")
  if($Text.Length -gt 0 -and $Text[-1] -ne "`n"){ $Text += "`n" }
  [System.IO.File]::WriteAllText($Path, $Text, $utf8)
}

$repoRoot = Resolve-RepoRoot
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

# Resolve Market/Symbol (env-first)
$m = (($Market + "")).Trim().ToUpperInvariant()
if(-not $m){ $m = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant() }
if(-not $m){ $m = "US" }
$Market = $m

$s = (($Symbol + "")).Trim().ToUpperInvariant()
if(-not $s){ $s = "NVDA" }
$Symbol = $s

# RunContext single-truth as_of_date
$rcPath = Join-Path $repoRoot "tools\Resolve-RunContext.ps1"
if(-not (Test-Path -LiteralPath $rcPath)){ throw "[FAIL-CLOSED] Missing Resolve-RunContext.ps1: $rcPath" }
$rcRaw = (& $rcPath -Market $Market -Symbol $Symbol | Out-String)
$rcRaw = (($rcRaw + "")).Trim()
$ix0 = $rcRaw.IndexOf("{"); $ix1 = $rcRaw.LastIndexOf("}")
if($ix0 -lt 0 -or $ix1 -le $ix0){ throw "[FAIL-CLOSED] Resolve-RunContext did not return JSON" }
$rc = ($rcRaw.Substring($ix0, ($ix1 - $ix0 + 1))) | ConvertFrom-Json
if(-not $rc -or -not $rc.as_of_date){ throw "[FAIL-CLOSED] Resolve-RunContext missing as_of_date" }
$todayLocal = Slice-Date ([string]$rc.as_of_date)

# Per-market logs dir
$gm = Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1"
if(-not (Test-Path -LiteralPath $gm)){ throw "[FAIL-CLOSED] Missing Get-MarketLogRoot.ps1: $gm" }
$logsDir = & "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $gm -Market $Market
if(-not $logsDir){ $logsDir = Join-Path (Join-Path $repoRoot "logs") $Market }
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$passPath = Join-Path $logsDir "phase4_validation_passed.json"
$outPath  = Join-Path $logsDir "phase4_status.json"

# Fail-closed defaults
$okToday = $false
$reason  = "missing_phase4_validation_passed"
$passAsOf = ""
$passOk = $false
$passParse = $false

if(Test-Path -LiteralPath $passPath){
  try{
    $j = Get-Content -LiteralPath $passPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $passParse = $true
    if($j -and ($j.PSObject.Properties.Name -contains "as_of_date")){ $passAsOf = Slice-Date ([string]$j.as_of_date) }

    # Accept multiple schema variants
    if($j -and ($j.PSObject.Properties.Name -contains "ok_today")){ $passOk = [bool]$j.ok_today }
    elseif($j -and ($j.PSObject.Properties.Name -contains "phase4_ok_today")){ $passOk = [bool]$j.phase4_ok_today }
    elseif($j -and ($j.PSObject.Properties.Name -contains "ok")){ $passOk = [bool]$j.ok }
    elseif($j -and ($j.PSObject.Properties.Name -contains "reason") -and (($j.reason + "") -eq "ok")){ $passOk = $true }

    if(-not $passAsOf){
      $okToday = $false
      $reason  = "phase4_pass_missing_as_of_date"
    } elseif($passAsOf -ne $todayLocal){
      $okToday = $false
      $reason  = ("stale_as_of_date pass_asof={0} today={1}" -f $passAsOf,$todayLocal)
    } elseif(-not $passOk){
      $okToday = $false
      $r = ""
      if($j -and ($j.PSObject.Properties.Name -contains "reason") -and $j.reason){ $r = [string]$j.reason }
      if(-not $r){ $r = "phase4_not_ok" }
      $reason = $r
    } else {
      $okToday = $true
      $reason  = "ok"
    }
  } catch {
    $okToday = $false
    $reason  = ("phase4_pass_parse_failed: " + $_.Exception.Message)
  }
}

$obj = [ordered]@{
  kind      = "phase4_status"
  ts_utc    = (Get-Date).ToUniversalTime().ToString("o")
  market    = $Market
  as_of_date= $todayLocal
  ok_today  = [bool]$okToday
  reason    = $reason
  evidence_paths = @($passPath)
  evidence_as_of_date = $passAsOf
  evidence_parse_ok = [bool]$passParse
}

Write-Utf8NoBomLf $outPath ($obj | ConvertTo-Json -Depth 8)
Write-Host ("[A2] wrote logs\{0} ok_today={1} as_of={2} reason={3}" -f "phase4_status.json",$okToday,$todayLocal,$reason) -ForegroundColor Cyan
exit 0
