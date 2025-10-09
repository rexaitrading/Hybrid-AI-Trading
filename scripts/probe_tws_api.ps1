param([string]$HostName="127.0.0.1",[int]$Port=7497,[int]$CidA=9721,[int]$CidB=0)
$ErrorActionPreference="Stop"
chcp 65001 > $null; [Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)

# A) RAW socket probe: send b'API\0' and read reply (fast)
$pyRaw = @"
import socket, sys
host='$HostName'; port=$Port
try:
    s = socket.create_connection((host,port), timeout=5)
    s.settimeout(3.0)
    s.sendall(b'API\\x00')
    data = s.recv(64)
    s.close()
    print('RAW-HANDSHAKE-BYTES:', len(data))
    print('RAW-HANDSHAKE-HEX:', data.hex())
    sys.exit(0 if data else 2)
except Exception as e:
    print('RAW-HANDSHAKE-ERR:', type(e).__name__, e)
    sys.exit(2)
"@
$tmpRaw = Join-Path $env:TEMP ("tws_raw_{0}.py" -f ([Guid]::NewGuid()))
[IO.File]::WriteAllText($tmpRaw,$pyRaw,[Text.UTF8Encoding]::new($false))
Write-Host ("== RAW socket probe ({0}:{1}) ==" -f $HostName, $Port)
python $tmpRaw
$rawOk = ($LASTEXITCODE -eq 0)
Remove-Item $tmpRaw -ErrorAction SilentlyContinue

# B) ib_insync probe: cidA then cidB (short timeouts; won’t hang)
$pyIB = @"
from ib_insync import IB
import sys
def probe(cid, host='$HostName', port=$Port):
    ib=IB()
    try:
        ok=ib.connect(host, port, clientId=cid, timeout=15)
        print(f'CID {cid}: connect:', ok, 'isConnected:', ib.isConnected())
    except Exception as e:
        print(f'CID {cid}: EXC', type(e).__name__, e)
    finally:
        try: ib.disconnect()
        except: pass
for cid in ($CidA, $CidB):
    probe(cid)
"@
$tmpIB = Join-Path $env:TEMP ("tws_ib_{0}.py" -f ([Guid]::NewGuid()))
[IO.File]::WriteAllText($tmpIB,$pyIB,[Text.UTF8Encoding]::new($false))
Write-Host ("`n== ib_insync probe (cid={0} then {1}) ==" -f $CidA, $CidB)
python $tmpIB
Remove-Item $tmpIB -ErrorAction SilentlyContinue