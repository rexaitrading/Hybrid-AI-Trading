param([int]$Port=4002, [int]$Tail=60)
$ErrorActionPreference='Stop'
"== port check =="
$conn = Get-NetTCPConnection -State Listen -LocalPort $Port -EA SilentlyContinue | Select-Object -First 1
if($conn){
  "listening on $($conn.LocalAddress):$Port  (PID $($conn.OwningProcess))"
  try{
    $p = Get-Process -Id $conn.OwningProcess -EA Stop
    "proc: $($p.ProcessName)  start: $($p.StartTime)  path: $($p.Path)"
  }catch{}
}else{
  "not listening on :$Port"
}
"`n== recent logs =="
Get-ChildItem C:\Jts\logs\*,C:\IBC\Logs\* -EA SilentlyContinue |
  Sort-Object LastWriteTime -Descending | Select-Object -First 2 |
  ForEach-Object { "---- $($_.FullName)"; Get-Content $_.FullName -Tail $Tail; "" }
