[CmdletBinding()]
param(
  [string]$OutPath = ".\logs\kill_switch_status.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Resolve-RepoRoot(){
  $rr = (($env:HAT_REPO_ROOT + "")).Trim()
  if($rr){ return [System.IO.Path]::GetFullPath($rr) }
  $toolsDir = Split-Path -Parent $PSCommandPath
  return [System.IO.Path]::GetFullPath((Split-Path -Parent $toolsDir))
}

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $enc = New-Object System.Text.UTF8Encoding($false)
  $norm = ($Text -replace "`r`n","`n")
  [System.IO.File]::WriteAllText($Path,$norm,$enc)
}

$repoRoot = Resolve-RepoRoot
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

$logsRoot = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Force -Path $logsRoot | Out-Null

$nowLocal = Get-Date
$kills = @()

# Framework fields (real detectors wired later):
# - ib_disconnect
# - unexpected_order
# - slippage_spike
# - volatility_shock
# - daily_loss_cap
#
# For now we create deterministic structure + allow manual arming via env vars (safe, not hidden):
#   HAT_KILL_SLIPPAGE=1
#   HAT_KILL_VOL=1
# etc.

$envKills = @{
  ib_disconnect    = (($env:HAT_KILL_IB + "") -in @("1","true","TRUE","yes","YES"))
  unexpected_order = (($env:HAT_KILL_ORDER + "") -in @("1","true","TRUE","yes","YES"))
  slippage_spike   = (($env:HAT_KILL_SLIPPAGE + "") -in @("1","true","TRUE","yes","YES"))
  volatility_shock = (($env:HAT_KILL_VOL + "") -in @("1","true","TRUE","yes","YES"))
  daily_loss_cap   = (($env:HAT_KILL_DAILYLOSS + "") -in @("1","true","TRUE","yes","YES"))
}

foreach($k in $envKills.Keys){
  if([bool]$envKills[$k]){
    $kills += [ordered]@{ kind=$k; active=$true; reason="env_armed"; fired_at_local=$nowLocal.ToString("yyyy-MM-dd HH:mm:ss") }
  }
}

$halt = ($kills.Count -gt 0)

$outObj = [ordered]@{
  schema = "kill_switch_status.v1"
  generated_at_local = $nowLocal.ToString("yyyy-MM-dd HH:mm:ss")
  halt_trading = $halt
  active_kills = $kills
}

$outJson = ($outObj | ConvertTo-Json -Depth 6)
$outFull = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutPath))
$odir = Split-Path -Parent $outFull
New-Item -ItemType Directory -Force -Path $odir | Out-Null
Write-Utf8NoBomLf -Path $outFull -Text $outJson

Write-Host ("[OK] wrote " + $outFull)
Write-Host ("[KILL] halt_trading=" + $halt + " active_kills=" + $kills.Count)