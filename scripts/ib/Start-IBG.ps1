[CmdletBinding()]
param(
  [ValidateSet("paper","live")] [string] $Mode = "paper",
  [string] $User      = $env:IB_USER,
  [string] $Password  = $env:IB_PWD,
  [string] $IbcRoot   = $env:IBC_ROOT,
  [string] $IbBase    = "C:\Jts\ibgateway",
  [switch] $KillExisting = $true,
  [int]    $ListenTimeoutSec = 180
)
$ErrorActionPreference=' + "'Stop'" + '
$PSNativeCommandUseErrorActionPreference=$true

function Get-LatestExe([string]$Base) {
  if (-not (Test-Path $Base)) { throw "IB Gateway base not found: $Base" }
  $dir = Get-ChildItem -Path $Base -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
  if(-not $dir){ throw "No versioned folder under $Base" }
  return (Join-Path $dir.FullName 'ibgateway.exe')
}
function Wait-Port([int]$Port,[int]$Sec){
  $deadline=(Get-Date).AddSeconds($Sec)
  while((Get-Date) -lt $deadline){
    $c=Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue|Select-Object -First 1
    if($c){return $c}; Start-Sleep -Milliseconds 500
  }; return $null
}

$exe = if(Test-Path (Join-Path $IbBase 'ibgateway.exe')){ Join-Path $IbBase 'ibgateway.exe' } else { Get-LatestExe -Base $IbBase }
if ($Mode -ieq 'live') { $apiPort = 7497 } else { $apiPort = 4002 }

if ($KillExisting) { 'ibgateway','java','javaw' | ForEach-Object { Get-Process $_ -ErrorAction SilentlyContinue | ForEach-Object { try{ $_ | Stop-Process -Force -ErrorAction SilentlyContinue } catch {} } }; Start-Sleep -Seconds 1 }

$useIbc = $false
if ($IbcRoot -and (Test-Path $IbcRoot)) { $useIbc = $true }

if ($useIbc) {
  if(-not $User -or -not $Password){ throw "Set -User/-Password OR `$env:IB_USER/IB_PWD for IBC auto-login." }
  $cfg = Join-Path $IbcRoot 'config.ini'
  if(-not (Test-Path $cfg)){
    $runMode = if($Mode -eq 'live'){'live'} else {'paper'}
    $content=@"
[Config]
IbLoginId=$User
IbPassword=$Password
TradingMode=$runMode
IbDir=$(Split-Path $exe)
UseTws=false
ReadOnlyLogin=no
AcceptIncomingConnection=false
AcceptNonBrokerageAccountWarning=yes
SaveTwsSettings=no
MinimizeMainWindow=Yes
"@
    [IO.File]::WriteAllText($cfg,$content,[Text.UTF8Encoding]::new($false))
  }
  Write-Host " Starting IB Gateway via IBC ($Mode) ..." -ForegroundColor Cyan
  $bat = if(Test-Path (Join-Path $IbcRoot 'ibcstart.bat')){ Join-Path $IbcRoot 'ibcstart.bin' } else { Join-Path $IbcRoot 'StartGateway.bat' }
  if(-not (Test-Path $bat)){ throw "IBC launcher not found in $IbcRoot" }
  Start-Process -FileName $bat -WorkingDirectory $IbcRoot | Out-Null
} else {
  Write-Host " Starting IB Gateway directly ($Mode) (manual login may be required)" -ForegroundColor Yellow
  Start-Process -FileName $exe -WorkingDirectory (Split-Path $exe) | Out-Null
}

Write-Host " Waiting up to $ListenTimeoutSec s for port $apiPort" -ForegroundColor Yellow
$c=Wait-Port -Port $apiPort -Sec $ListenTimeoutSec
if($c){ " IBG listening on $($c.LocalAddress):$($c.LocalPort) PID=$($c.OwningProcess)" }
else { Write-Warning "IBG did not open port $apiPort in $ListenTimeoutSec. Check GUI/2FA/firewall." }
