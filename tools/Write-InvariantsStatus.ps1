[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market = "US",

  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",

  [ValidateSet("PAPER","PAPERLIVE","LIVE")]
  [string]$Mode = "PAPERLIVE",

  [switch]$NoConsole
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

try {
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  [Console]::OutputEncoding = $utf8
  [Console]::InputEncoding  = $utf8
  $global:OutputEncoding    = $utf8
} catch { }

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $t = ($Text -replace "`r`n","`n" -replace "`r","`n")
  if($t.Length -eq 0 -or $t[-1] -ne "`n"){ $t += "`n" }
  [System.IO.File]::WriteAllText($Path, $t, (New-Object System.Text.UTF8Encoding($false)))
}

function Fail([string]$m){
  if(-not $NoConsole){ Write-Host ("[FAIL-CLOSED] " + $m) -ForegroundColor Red }
  exit 2
}

function Slice10([string]$d){
  $s = ([string]$d).Trim()
  if($s.Length -ge 10){ return $s.Substring(0,10) }
  return $s
}

function Read-JsonFromStdout([string]$raw){
  $r = (($raw + "")).Trim()
  $i0 = $r.IndexOf('{'); $i1 = $r.LastIndexOf('}')
  if($i0 -lt 0 -or $i1 -le $i0){ return $null }
  try { return ($r.Substring($i0, ($i1-$i0+1)) | ConvertFrom-Json -ErrorAction Stop) } catch { return $null }
}

function Try-GetViolations([object]$dash){
  # Return: violations array (strings/objects), source_key, and optional inv_ok
  try {
    if(-not $dash){ return @(@(), $null, $null) }

    # Preferred schema: dash.invariants = { ok: bool, violations: [] }
    if($dash.PSObject.Properties.Name -contains "invariants"){
      $inv = $dash.invariants
      if($inv -and ($inv.PSObject.Properties.Name -contains "violations")){
        $v = @($inv.violations)
        $invOk = $null
        if($inv.PSObject.Properties.Name -contains "ok"){
          try { $invOk = [bool]$inv.ok } catch { $invOk = $null }
        }
        return @($v, "invariants.violations", $invOk)
      }
    }

    # Fallback keys (legacy)
    $keys = @("invariant_violations","invariants_violations","violations","viol","violations_list")
    foreach($k in $keys){
      if($dash.PSObject.Properties.Name -contains $k){
        $vv = $dash.$k
        if($null -eq $vv){ return @(@(), $k, $null) }
        if($vv -is [System.Array]){ return @(@($vv), $k, $null) }
        return @(@($vv), $k, $null)
      }
    }

    return @(@(), $null, $null)
  } catch {
    return @(@(), $null, $null)
  }
}

$mk = (($Market + "")).Trim().ToUpperInvariant()
$sy = (($Symbol + "")).Trim().ToUpperInvariant()

# Policy A: non-US markets only support NVDA
if($mk -ne "US" -and $sy -in @("SPY","QQQ")){
  Fail ("PolicyA symbol_not_applicable_for_market market=" + $mk + " symbol=" + $sy)
}

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
try { $repoRoot = (Resolve-Path -LiteralPath $repoRoot -ErrorAction Stop).Path } catch { }
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

$rcPath   = Join-Path $toolsDir "Resolve-RunContext.ps1"
$dashPath = Join-Path $toolsDir "Build-OpsDashboard.ps1"

foreach($p in @($rcPath,$dashPath)){
  if(-not (Test-Path -LiteralPath $p)){ Fail ("missing tool: " + $p) }
}

# Resolve RunContext (single truth)
$rcRaw = (& $rcPath -Market $mk -Symbol $sy 2>&1 | Out-String)
$rcObj = Read-JsonFromStdout $rcRaw
if(-not $rcObj){ Fail ("Resolve-RunContext did not return JSON market=" + $mk) }

if(-not ($rcObj.PSObject.Properties.Name -contains "logs_dir_out")){ Fail "RunContext missing logs_dir_out" }
if(-not ($rcObj.PSObject.Properties.Name -contains "as_of_date")){ Fail "RunContext missing as_of_date" }

$logsDirOut = ([string]$rcObj.logs_dir_out).Trim()
if(-not $logsDirOut){ Fail "RunContext logs_dir_out empty" }
if(-not (Test-Path -LiteralPath $logsDirOut)){ New-Item -ItemType Directory -Force -Path $logsDirOut | Out-Null }

$asOf = Slice10 ([string]$rcObj.as_of_date)

# Output paths
$dashOut = Join-Path $logsDirOut "ops_dashboard.json"
$outPath = Join-Path $logsDirOut "invariants_status.json"

# Set env for called tools (authoritative session context)
$env:HAT_MODE      = $Mode
$env:HAT_MARKET    = $mk
$env:HAT_SYMBOL    = $sy
$env:HAT_ASOF_DATE = $asOf
$env:HAT_LOGS_DIR  = $logsDirOut

# Always try to (re)build dashboard JSON (source of invariants)
$dashExit = 0
$dashErr  = ""
try {
  & $dashPath -Market $mk -Symbol $sy -Mode $Mode -OutPath $dashOut -EmitConsole:(-not $NoConsole) | Out-Null
  if($LASTEXITCODE -ne $null -and [int]$LASTEXITCODE -ne 0){ $dashExit = [int]$LASTEXITCODE }
} catch {
  $dashExit = 2
  $dashErr = $_.Exception.Message
}

# Load dashboard JSON (even if dashExit != 0, try to read whatever was written)
$dashObj = $null
try {
  if(Test-Path -LiteralPath $dashOut){
    $dashRaw = Get-Content -LiteralPath $dashOut -Raw -Encoding UTF8
    if($dashRaw){ $dashObj = ($dashRaw | ConvertFrom-Json -ErrorAction Stop) }
  }
} catch { $dashObj = $null }

$violations = @()
$violKey = $null
$reason = ""
$ok = $false

if(-not $dashObj){
  $ok = $false
  $reason = "ops_dashboard_json_missing_or_unreadable"
} else {
  $pair = Try-GetViolations $dashObj
  $violations = @($pair[0])
  $violKey = $pair[1]
  $invOk = $pair[2]
  if(-not $violKey){
    $ok = $false
    $reason = "violations_field_missing"
    $violations = @()
  } else {
    if($null -ne $invOk){
      $ok = [bool]$invOk
    } else {
      $ok = ($violations.Count -eq 0)
    }
    if($ok){ $reason = "ok" } else { $reason = "violations_present" }
  }

}

# Build invariant artifact (always emitted)
$artifact = [pscustomobject]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  market = $mk
  symbol = $sy
  run_mode = $Mode
  as_of_date = $asOf
  logs_dir_out = $logsDirOut

  ok = $ok
  reason = $reason

  violations = @($violations)
  violations_source_key = $violKey

  ops_dashboard_path = $dashOut
  ops_dashboard_exit = $dashExit
  ops_dashboard_error = $dashErr
}

Write-Utf8NoBomLf $outPath ($artifact | ConvertTo-Json -Depth 8)

if(-not $NoConsole){
  $c = if($ok){ "Green" } else { "Red" }
  Write-Host ("[INV] wrote " + $outPath + " ok=" + $ok + " viols=" + $artifact.violations.Count + " reason=" + $reason) -ForegroundColor $c
}

if(-not $ok){ exit 2 }
exit 0
