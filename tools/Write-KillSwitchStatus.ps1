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
# Extract JSON from stdout safely
$r = (($rcRaw + "")).Trim()
$i0 = $r.IndexOf('{'); $i1 = $r.LastIndexOf('}')
if($i0 -lt 0 -or $i1 -le $i0){ Fail ("Resolve-RunContext did not return JSON (market=" + $mk + ")") }
$rcObj = $null
try { $rcObj = ($r.Substring($i0, ($i1-$i0+1)) | ConvertFrom-Json -ErrorAction Stop) } catch { Fail "Resolve-RunContext JSON parse failed" }

if(-not ($rcObj.PSObject.Properties.Name -contains "logs_dir_out")){ Fail "RunContext missing logs_dir_out" }
if(-not ($rcObj.PSObject.Properties.Name -contains "as_of_date")){ Fail "RunContext missing as_of_date" }

$logsDirOut = ([string]$rcObj.logs_dir_out).Trim()
if(-not $logsDirOut){ Fail "RunContext logs_dir_out empty" }
if(-not (Test-Path -LiteralPath $logsDirOut)){ New-Item -ItemType Directory -Force -Path $logsDirOut | Out-Null }

$asOf = Slice10 ([string]$rcObj.as_of_date)
$outPath = Join-Path $logsDirOut "killswitch_status.json"

# Set env for dashboard (authoritative session context)
$env:HAT_MODE      = $Mode
$env:HAT_MARKET    = $mk
$env:HAT_SYMBOL    = $sy
$env:HAT_ASOF_DATE = $asOf
$env:HAT_LOGS_DIR  = $logsDirOut

# Call dashboard and parse its [DASH] line
# Call dashboard in a child PowerShell to capture host output reliably (Write-Host)
$dashArgs = @(
  "-NoProfile","-ExecutionPolicy","Bypass","-File",$dashPath,
  "-Market",$mk,"-Symbol",$sy,"-Mode",$Mode
)
$dashRaw = (& powershell @dashArgs 2>&1 | Out-String)

$dashLine = ($dashRaw -split "\r?\n" | Where-Object { $_ -match "^\[DASH\]" } | Select-Object -Last 1)
if(-not $dashLine){
  # Always emit, but fail-closed semantics: kill=true if we cannot parse dashboard line
  $obj = [pscustomobject]@{
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    market = $mk
    symbol = $sy
    run_mode = $Mode
    as_of_date = $asOf
    logs_dir_out = $logsDirOut
    kill = $true
    top_reason = "dash_line_missing"
    signal = "DASH_PARSE_ERR"
    age_min = $null
    max_age_min = $null
    raw_tail = ($dashRaw.Substring([Math]::Max(0,$dashRaw.Length-400)))
    ok = $false
  }
  Write-Utf8NoBomLf $outPath ($obj | ConvertTo-Json -Depth 6)
  if(-not $NoConsole){ Write-Host ("[KILL] wrote " + $outPath + " kill=True reason=dash_line_missing") -ForegroundColor Yellow }
  exit 2
}

# Parse key=value tokens
$tokens = @{}
foreach($part in ($dashLine -split '\s+')){
  if($part -match '^(?<k>[^=]+)=(?<v>.+)$'){
    $tokens[$Matches['k']] = $Matches['v']
  }
}

$kill = $false
if($tokens.ContainsKey('kill')){
  $kill = (($tokens['kill'] + "") -eq 'True' -or ($tokens['kill'] + "") -eq 'true')
} else {
  $kill = $true
}

$ageMin = $null
if($tokens.ContainsKey('age_min')){
  try { $ageMin = [int]($tokens['age_min']) } catch { $ageMin = $null }
}

$maxMin = $null
if($tokens.ContainsKey('max')){
  try { $maxMin = [int]($tokens['max']) } catch { $maxMin = $null }
}

$top = if($tokens.ContainsKey('top')){ [string]$tokens['top'] } else { "unknown" }
$sig = if($tokens.ContainsKey('signal')){ [string]$tokens['signal'] } else { "unknown" }

$obj2 = [pscustomobject]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  market = $mk
  symbol = $sy
  run_mode = $Mode
  as_of_date = $asOf
  logs_dir_out = $logsDirOut
  kill = $kill
  top_reason = $top
  signal = $sig
  age_min = $ageMin
  max_age_min = $maxMin
  dash_line = $dashLine
  ok = $true
}

Write-Utf8NoBomLf $outPath ($obj2 | ConvertTo-Json -Depth 6)

if(-not $NoConsole){
  $c = if($kill){ "Red" } else { "Green" }
  Write-Host ("[KILL] wrote " + $outPath + " kill=" + $kill + " top=" + $top + " signal=" + $sig) -ForegroundColor $c
}

if($kill){ exit 2 }
exit 0
