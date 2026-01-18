[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market = "US",

  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",

  [ValidateSet("PAPER","PAPERLIVE","LIVE")]
  [string]$Mode = "PAPERLIVE",

  # Optional: write merged dashboard JSON to this path
  [string]$OutPath = "",

  [switch]$EmitConsole = $true
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
  if($EmitConsole){ Write-Host ("[FAIL-CLOSED] " + $m) -ForegroundColor Red }
  exit 2
}
function Read-JsonFromStdout([string]$raw){
  $r = (($raw + "")).Trim()
  $i0 = $r.IndexOf('{'); $i1 = $r.LastIndexOf('}')
  if($i0 -lt 0 -or $i1 -le $i0){ return $null }
  try { return ($r.Substring($i0, ($i1-$i0+1)) | ConvertFrom-Json -ErrorAction Stop) } catch { return $null }
}

function Read-JsonFile([string]$Path){
  try {
    if(-not (Test-Path -LiteralPath $Path)){ return $null }
    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    if(-not $raw){ return $null }
    return ($raw | ConvertFrom-Json -ErrorAction Stop)
  } catch { return $null }
}
function Resolve-RunContextJson([string]$Market,[string]$Symbol){
  $rcPath = Join-Path (Split-Path -Parent $PSCommandPath) "Resolve-RunContext.ps1"
  if(-not (Test-Path -LiteralPath $rcPath)){ return $null }
  $rcRaw = (& $rcPath -Market $Market -Symbol $Symbol 2>&1 | Out-String)
  return (Read-JsonFromStdout $rcRaw)
}
$mk = (($Market + "")).Trim().ToUpperInvariant()
$sy = (($Symbol + "")).Trim().ToUpperInvariant()
$rm = (($Mode + "")).Trim().ToUpperInvariant()
if($rm -notin @("PAPER","PAPERLIVE","LIVE")){ Fail ("invalid -Mode=" + $Mode) }

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
try { $repoRoot = (Resolve-Path -LiteralPath $repoRoot -ErrorAction Stop).Path } catch { }
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

$dashPath = Join-Path $toolsDir "Build-OpsDashboard.ps1"
$invPath  = Join-Path $toolsDir "Write-InvariantsStatus.ps1"
$ksPath   = Join-Path $toolsDir "Write-KillSwitchStatus.ps1"
$opsPath  = Join-Path $toolsDir "Write-OpsReadyStatus.ps1"

foreach($p in @($dashPath,$invPath,$ksPath,$opsPath)){
  if(-not (Test-Path -LiteralPath $p)){ Fail ("missing tool: " + $p) }
}
# --- Unified producer model (single truth) ---
# Resolve RunContext to locate logs_dir_out
$rcObj = Resolve-RunContextJson -Market $mk -Symbol $sy
if(-not $rcObj){ Fail "Resolve-RunContext did not return JSON" }
if(-not ($rcObj.PSObject.Properties.Name -contains "logs_dir_out")){ Fail "RunContext missing logs_dir_out" }
$logsDirOut = ([string]$rcObj.logs_dir_out).Trim()
if(-not $logsDirOut){ Fail "RunContext logs_dir_out empty" }

# Run orchestrator producer (writes ops_ready_status.json + component artifacts)
& $opsPath -Market $mk -Symbol $sy -Mode $rm -NoConsole | Out-Null

$opsJsonPath = Join-Path $logsDirOut "ops_ready_status.json"
$opsObj = Read-JsonFile $opsJsonPath
if(-not $opsObj){ Fail "ops_ready_status.json missing or unreadable" }

# Optional embeds from ops_ready_status.paths
$dashObj = $null
$ksObj = $null
$invObj = $null
try {
  if($opsObj.PSObject.Properties.Name -contains "paths"){
    $pp = $opsObj.paths
    if($pp -and ($pp.PSObject.Properties.Name -contains "ops_dashboard")){ $dashObj = Read-JsonFile ([string]$pp.ops_dashboard) }
    if($pp -and ($pp.PSObject.Properties.Name -contains "killswitch_status")){ $ksObj = Read-JsonFile ([string]$pp.killswitch_status) }
    if($pp -and ($pp.PSObject.Properties.Name -contains "invariants_status")){ $invObj = Read-JsonFile ([string]$pp.invariants_status) }
  }
} catch { }

# ok_to_trade: prefer ops_ready_status.trade_allowed; else ops_ready_status.ops_ready
$ok = $false
try {
  if($opsObj.PSObject.Properties.Name -contains "trade_allowed"){ $ok = [bool]$opsObj.trade_allowed }
  elseif($opsObj.PSObject.Properties.Name -contains "ops_ready"){ $ok = [bool]$opsObj.ops_ready }
} catch { $ok = $false }

$out = [ordered]@{
  market = $mk
  symbol = $sy
  mode = $rm
  now_local = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
  repo_root = $repoRoot
  dotnet_cwd = [System.Environment]::CurrentDirectory

  ops_ready = $opsObj
  invariants = $invObj
  kill_switch = $ksObj
  dashboard = $dashObj

  ok_to_trade = $ok
}
$json = ($out | ConvertTo-Json -Depth 12)

if($OutPath){
  try {
    $op = $OutPath
    if(-not [System.IO.Path]::IsPathRooted($op)){
      $op = Join-Path $repoRoot $op
    }
    $parent = Split-Path -Parent $op
    if($parent){ New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    Write-Utf8NoBomLf -Path $op -Text $json
    $out["out_path"] = $op
    $json = ($out | ConvertTo-Json -Depth 12)
  } catch {
    Fail "failed to write OutPath"
  }
}

if($EmitConsole){
  Write-Host $json
} else {
  $json
}
