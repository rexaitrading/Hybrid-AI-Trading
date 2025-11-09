# C:\Dev\HybridAITrading\tools\IBG-Diag.ps1  (PS 5.1 safe; UTF-8 no BOM + LF)
[CmdletBinding()]
param(
  [string] $TargetHost      = '127.0.0.1',
  [int[]]  $Ports           = @(4002,4001),
  [int]    $IntervalSeconds = 30,
  [int]    $DurationMinutes = 30,
  [string] $IbcLogDir       = 'C:\IBC\Logs',
  [string] $IbgRootDir      = 'C:\Jts\ibgateway',
  [string] $OutRoot         # <-- do NOT default here in PS 5.1
)

$ErrorActionPreference='Stop'
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

# Resolve script directory safely in PS 5.1
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $OutRoot -or $OutRoot -eq '') { $OutRoot = Join-Path $ScriptDir '..\artifacts\ibg_diag' }

function New-DirIfNeeded([string]$p){ if(-not(Test-Path $p)){ New-Item -ItemType Directory -Force -Path $p | Out-Null } }
function Write-Text([string]$path,[string]$text){ [System.IO.File]::WriteAllText($path,($text -replace "`r?`n","`n"),$Utf8NoBom) }
function Add-Text([string]$path,[string]$text){ if(-not(Test-Path $path)){ Write-Text $path '' }; $b=$Utf8NoBom.GetBytes(($text -replace "`r?`n","`n")); $fs=[System.IO.File]::Open($path,[System.IO.FileMode]::Append,[System.IO.FileAccess]::Write,[System.IO.FileShare]::ReadWrite); try{$fs.Write($b,0,$b.Length)}finally{$fs.Close()} }
function Write-Log([string]$name,[string]$text){ $path=Join-Path $script:RunDir $name; Add-Text -path $path -text ($text + "`n") }

function Test-Tcp([string]$host,[int]$port,[int]$timeoutMs=2000){
  $ok=$false; $err=$null; $c=New-Object System.Net.Sockets.TcpClient
  try{ $iar=$c.BeginConnect($host,$port,$null,$null); if($iar.AsyncWaitHandle.WaitOne($timeoutMs)){ $c.EndConnect($iar); if($c.Connected){$ok=$true} } else { $err="timeout ${timeoutMs}ms" } }
  catch{ $err=$_.Exception.Message } finally{ try{$c.Close()}catch{} }
  [pscustomobject]@{Host=$host;Port=$port;Ok=$ok;Error=$err;Ts=(Get-Date)}
}
function Get-Owner([int]$Port){
  $l=Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
  if(-not $l){return $null}; $p=Get-Process -Id $l.OwningProcess -ErrorAction SilentlyContinue; $cmd=$null
  try{ $w=Get-CimInstance Win32_Process -Filter ("ProcessId={0}" -f $l.OwningProcess); if($w){$cmd=$w.CommandLine} }catch{}
  [pscustomobject]@{Port=$Port;PID=$l.OwningProcess;Path=$p.Path;CPU=if($p){[math]::Round($p.CPU,2)}else{$null};WS_MB=if($p){[math]::Round($p.WorkingSet/1MB,1)}else{$null};Start=if($p){$p.StartTime}else{$null};Cmd=$cmd}
}
function Get-LastLogs([string]$IbcLogDir,[string]$IbgRootDir,[int]$Tail=80){
  $sb=New-Object System.Text.StringBuilder; [void]$sb.AppendLine("== LOG SNAPSHOT @ $(Get-Date -Format s) ==")
  if(Test-Path $IbcLogDir){ [void]$sb.AppendLine("---- IBC logs ($IbcLogDir) ----")
    Get-ChildItem $IbcLogDir -File -Recurse -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 2 | %{
      [void]$sb.AppendLine("`n[$($_.FullName)]"); try{ (Get-Content $_.FullName -Tail $Tail) | % { [void]$sb.AppendLine($_) } }catch{} } }
  else{ [void]$sb.AppendLine("IBC log dir not found: $IbcLogDir") }
  if(Test-Path $IbgRootDir){
    $ver=Get-ChildItem $IbgRootDir -Directory -ErrorAction SilentlyContinue | ?{ $_.Name -match '^\d{4}' } | Sort-Object Name -Descending | Select-Object -First 1
    if($ver){ [void]$sb.AppendLine("---- IBG logs ($($ver.FullName)) ----")
      Get-ChildItem $ver.FullName -Filter *.log -File | Sort-Object LastWriteTime -Descending | Select-Object -First 3 | %{
        [void]$sb.AppendLine("`n[$($_.FullName)]"); try{ (Get-Content $_.FullName -Tail $Tail) | % { [void]$sb.AppendLine($_) } }catch{} } }
    else{ [void]$sb.AppendLine("No IBG version folder under $IbgRootDir") } }
  else{ [void]$sb.AppendLine("IBG root not found: $IbgRootDir") }
  $sb.ToString()
}
function Get-EventDiag([int]$Minutes=30){
  $s=New-Object System.Text.StringBuilder; [void]$s.AppendLine("== EVENTS last $Minutes min @ $(Get-Date -Format s) ==")
  try{ [void]$s.AppendLine("--- Schannel (System) ---")
    $sys=Get-WinEvent -ErrorAction SilentlyContinue -FilterHashtable @{LogName='System';ProviderName='Schannel';StartTime=(Get-Date).AddMinutes(-1*$Minutes)}
    foreach($e in $sys){ [void]$s.AppendLine(("{0:u}  ID={1}  {2}`n{3}" -f $e.TimeCreated,$e.Id,$e.LevelDisplayName,$e.Message)) } }catch{}
  try{ [void]$s.AppendLine("`n--- Application (Java/IB*) ---")
    $app=Get-WinEvent -ErrorAction SilentlyContinue -FilterHashtable @{LogName='Application';StartTime=(Get-Date).AddMinutes(-1*$Minutes)}
    foreach($e in $app){ if($e.ProviderName -match 'Java|IBGateway|IBController|IB' -or $e.LevelDisplayName -in @('Error','Critical')){
      [void]$s.AppendLine(("{0:u}  {1}  ID={2}  {3}`n{4}" -f $e.TimeCreated,$e.ProviderName,$e.Id,$e.LevelDisplayName,$e.Message)) } } }catch{}
  $s.ToString()
}
function Get-SystemHealth{
  $s=New-Object System.Text.StringBuilder; [void]$s.AppendLine("== SYSTEM HEALTH @ $(Get-Date -Format s) ==")
  try{ $tz=(Get-TimeZone).Id; [void]$s.AppendLine("TimeZone: $tz"); $ntp=w32tm /query /status 2>$null; [void]$s.AppendLine(($ntp -join "`n")) }catch{}
  try{ [void]$s.AppendLine("Power plan + NIC power saving:"); $plan=powercfg /GetActiveScheme 2>$null; [void]$s.AppendLine(($plan -join "`n"))
    $n=Get-NetAdapter -ErrorAction SilentlyContinue; foreach($x in $n){ $p=(Get-NetAdapterPowerManagement -Name $x.Name -ErrorAction SilentlyContinue)
      if($p){ [void]$s.AppendLine(("{0}: AllowSleep={1}  WakeOnMagic={2}  PacketCoalesce={3}" -f $x.Name,$p.AllowComputerToTurnOffDevice,$p.WakeOnMagicPacket,$p.PacketCoalescing)) } } }catch{}
  try{ [void]$s.AppendLine("Firewall rules for javaw.exe:"); $rules=Get-NetFirewallRule -ErrorAction SilentlyContinue | ?{ $_.DisplayName -match 'javaw|Java' }
    foreach($r in $rules){ [void]$s.AppendLine(("{0}  {1}  Enabled={2}  Action={3}" -f $r.Direction,$r.DisplayName,$r.Enabled,$r.Action)) } }catch{}
  try{ [void]$s.AppendLine("DNS resolution for IB hosts:"); $hosts=@('gw1.ibllc.com','gw2.ibllc.com','cdn.interactivebrokers.com')
    foreach($h in $hosts){ try{ $ips=[System.Net.Dns]::GetHostAddresses($h) | % { $_.IPAddressToString } | Sort-Object -Unique; [void]$s.AppendLine("$h -> $($ips -join ', ')") }
      catch{ [void]$s.AppendLine("$h -> DNS FAIL: $($_.Exception.Message)") } } }catch{}
  $s.ToString()
}
function Write-Summary{
  $sum=New-Object System.Text.StringBuilder; [void]$sum.AppendLine("## Findings (`$(Get-Date -Format s)`)")
  $cp=Join-Path $script:RunDir 'connectivity.csv'
  if(Test-Path $cp){ $conn=Get-Content $cp; $fails=($conn|Select-String 'FAIL').Count
    if($fails -gt 0){ [void]$sum.AppendLine(("**RED**: Detected {0} TCP failures to {1}:{2}. Check network/power/TLS." -f $fails,$script:TargetHost,($script:Ports -join ','))) }
    else{ [void]$sum.AppendLine(("**GREEN**: No TCP connect failures to {0}:{1}." -f $script:TargetHost,($script:Ports -join ','))) } }
  $ep=Join-Path $script:RunDir 'events.txt'
  if(Test-Path $ep){ $ev=Get-Content $ep -Raw
    if($ev -match 'Schannel' -and $ev -match 'fatal alert|cert|handshake|trust|tls'){ [void]$sum.AppendLine("**RED**: Schannel/TLS errors present. Check TLS/time/cert; set `UseSSL=false` for 4001/4002 if required.") }
    if($ev -match 'Exception|Faulting application name|Java'){ [void]$sum.AppendLine("**RED**: Java/IBGateway crashes logged in Application event log.") } }
  $lp=Join-Path $script:RunDir 'logs.txt'
  if(Test-Path $lp){ $lg=Get-Content $lp -Raw
    if($lg -match 'AutoRestart|Shutting down|Login.*failed|socket.*closed|Lost.*connection|SSL|TLS'){ [void]$sum.AppendLine("**YELLOW/RED**: IBC/IBG logs show disconnect/restart indicators  inspect `logs.txt`.") }
    else{ [void]$sum.AppendLine("Logs snapshot captured; no obvious disconnect strings found.") } }
  [void]$sum.AppendLine(("Artifacts: `{0}" -f $script:RunDir))
  Write-Text -path (Join-Path $script:RunDir 'Summary.md') -text $sum.ToString()
}

# MAIN
New-DirIfNeeded $OutRoot
$stamp  = Get-Date -Format 'yyyyMMdd_HHmmss'
$RunDir = Join-Path $OutRoot ("diag_{0}" -f $stamp)
$script:RunDir = $RunDir
New-DirIfNeeded $RunDir

Write-Log -Name 'Summary.md' -Text ("# IBG Diagnostic Run {0}`nTargetHost: {1}  Ports: {2}`nInterval: {3}s  Duration: {4}m`n" -f $stamp,$TargetHost,($Ports -join ','),$IntervalSeconds,$DurationMinutes)
Write-Log -Name 'system_health.txt' -Text (Get-SystemHealth)
Write-Log -Name 'events.txt'        -Text (Get-EventDiag -Minutes ([int][math]::Max(1,$DurationMinutes)))
Write-Log -Name 'logs.txt'          -Text (Get-LastLogs -IbcLogDir $IbcLogDir -IbgRootDir $IbgRootDir)

$iterations = [int][math]::Max(1,[math]::Ceiling(($DurationMinutes*60.0)/$IntervalSeconds))
for($i=1;$i -le $iterations;$i++){
  $ts=Get-Date -Format s
  foreach($p in $Ports){
    $o=Get-Owner -Port $p
    $line = if($o){ "{0} PORT={1} PID={2} PATH={3} WS={4}MB CPU={5} Start={6}" -f $ts,$o.Port,$o.PID,$o.Path,$o.WS_MB,$o.CPU,$o.Start } else { "{0} PORT={1} not listening" -f $ts,$p }
    Write-Log -Name 'process.csv' -Text $line
    $tcp=Test-Tcp -host $TargetHost -port $p -timeoutMs 2000
    $ok = if($tcp.Ok){'OK'}else{'FAIL'}; $err = if($tcp.Error){" ($($tcp.Error))"}else{''}
    Write-Log -Name 'connectivity.csv' -Text ("{0}, {1}, {2}, {3}{4}" -f $tcp.Ts.ToString('s'),$tcp.Host,$tcp.Port,$ok,$err)
  }
  if(($i % 5) -eq 0){
    $mins=[int][math]::Ceiling(($IntervalSeconds*5.0)/60.0)
    Write-Log -Name 'events.txt' -Text (Get-EventDiag -Minutes $mins)
    Write-Log -Name 'logs.txt'   -Text (Get-LastLogs -IbcLogDir $IbcLogDir -IbgRootDir $IbgRootDir)
  }
  if($i -lt $iterations){ Start-Sleep -Seconds $IntervalSeconds }
}
Write-Summary
Write-Log -Name 'Summary.md' -Text "`nDone."
Write-Output ("Diagnostic complete -> {0}" -f $RunDir)
