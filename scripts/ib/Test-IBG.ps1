[CmdletBinding()] param([ValidateSet("paper","live")] [string] $Mode = "paper")
$ErrorActionPreference=' + "'Stop'" + '
$port = if ($Mode -eq "live") { 7497 } else { 4002 }
$c=Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue|Select-Object -First 1
if($c){ "{0}:{1} listening (PID {2})" -f $c.LocalAddress,$c.LocalPort,$c.OwningProcess } else { "Port $port not listening" }
"WinHTTP proxy: " + ( & netsh winhttp show proxy | Out-String ).Trim()
"Active routes:"; Get-NetRoute -DestinationPrefix "0.0.0.0/0" | ft -Auto
