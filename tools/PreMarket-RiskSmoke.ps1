param(
  [string]$Channel      = '#all-hybridaitrading',
  [string]$Repo         = 'C:\Dev\HybridAITrading',
  [string]$Python       = 'python',
  [int]   $MinUptimeSec = 30,
  [int]   $MaxRssMB     = 2000
)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
. 'C:\IBC\Watch-IBG.Functions.ps1'

function Load-Heartbeat { $p='C:\IBC\status\ibg_status.json'; if(Test-Path $p){ try{Get-Content $p|ConvertFrom-Json}catch{}} }
function Test-IBGHealthy { param([int]$MaxRssMB=2000,[int]$MinUptimeSec=30)
  $hb=Load-Heartbeat; if(-not $hb){return $false}
  if(-not $hb.portUp){return $false}
  if($hb.uptimeSec -lt $MinUptimeSec){return $false}
  if($hb.rssMB -and $hb.rssMB -gt $MaxRssMB){return $false}
  return $true
}

function Run-TestNode {
  param([string]$NodeId,[string]$Repo,[string]$Python='python')
  if(Test-Path $Repo){Push-Location $Repo}else{throw "Repo not found: $Repo"}
  try{
    $sw=[Diagnostics.Stopwatch]::StartNew()
    $output=& $Python -m pytest -q $NodeId -s --maxfail=1 2>&1
    $code=$LASTEXITCODE; $sw.Stop(); $dur=[math]::Round($sw.Elapsed.TotalSeconds,2)
    $status=if($code -eq 0){'pass'}else{'fail'}
    $tail=($output|Select-Object -Last 30) -join "`n"
    [pscustomobject]@{node=$NodeId;status=$status;seconds=$dur;tail=$tail;code=$code}
  } finally {Pop-Location}
}

function Post-SmokeResult {
  param([string]$Channel,[object]$Heartbeat,[object[]]$Results)
  $failed=$Results|Where-Object {$_.status -ne 'pass'}; $ok= -not $failed
  $lines = foreach($r in $Results){ $mark=if($r.status -eq 'pass'){''}else{''}; "{0} {1}  ({2}s)" -f $mark,$r.node,$r.seconds }
  $body = $lines -join "`n"
  $ver= if($Heartbeat.gw -and $Heartbeat.gw.ver){$Heartbeat.gw.ver}else{'unknown'}
  $exe= if($Heartbeat.path){$Heartbeat.path}elseif($Heartbeat.gw -and $Heartbeat.gw.exe){$Heartbeat.gw.exe}else{'n/a'}
  $upt= if($Heartbeat.uptimeSec){"{0:h\:mm\:ss}" -f ([timespan]::FromSeconds([int]$Heartbeat.uptimeSec))}else{"n/a"}
  $rss= if($Heartbeat.rssMB){"{0:N0} MB" -f $Heartbeat.rssMB}else{"n/a"}
  $emoji= if($ok){""}else{""}
  $header="$emoji Risk-first smoke  IBG OK :4002 · pid $($Heartbeat.pid) · v$ver`n$exe`nUptime $upt · RSS $rss"
  $text=$header+"`n`n"+$body
  if(-not $ok){
    $firstFail=$failed|Select-Object -First 1
    if($firstFail){
      $bt=[char]96; $fence="$bt$bt$bt"
      $text+="`n`n$($fence)$($firstFail.tail)$($fence)"
    }
  }
  Invoke-SlackJson -Method 'chat.postMessage' -Body @{channel=$Channel;text=$text;mrkdwn=$true} | Out-Null
  return $ok
}

# 0) Wait for IBG and write fresh heartbeat
$s = Wait-Until-IBGUp -TimeoutSec 60
Write-Heartbeat -PortUp $s.PortUp -GwPid ($s.GW_PID -as [int]) -Uptime $s.Uptime -CPU $s.CPU -RSS $s.RSS -GwInfo $s.Info -GwPath $s.Path
$hb = Load-Heartbeat

# 1) Gate
if(-not (Test-IBGHealthy -MinUptimeSec $MinUptimeSec -MaxRssMB $MaxRssMB)){
  Invoke-SlackJson -Method 'chat.postMessage' -Body @{
    channel=$Channel; text=" IBG not healthy  portUp=$($hb.portUp) uptimeSec=$($hb.uptimeSec) rssMB=$($hb.rssMB). Aborting smoke."; mrkdwn=$true }|Out-Null
  exit 2
}

# 2) Risk-first nodes
$nodes=@(
  'tests\test_risk_manager_more_cov.py::test_daily_loss_flag_flip_and_reset',
  'tests\test_risk_halts_more.py::test_record_close_positive_resets_losers_and_on_fill_increments'
)

# 3) Run tests
$results=@()
foreach($n in $nodes){
  try{$results+=(Run-TestNode -NodeId $n -Repo $Repo -Python $Python)}
  catch{$results+=[pscustomobject]@{node=$n;status='fail';seconds=0;tail=$_.Exception.Message;code=1}}
}

# 4) Post and exit code
$ok=Post-SmokeResult -Channel $Channel -Heartbeat $hb -Results $results
if($ok){exit 0}else{exit 3}
