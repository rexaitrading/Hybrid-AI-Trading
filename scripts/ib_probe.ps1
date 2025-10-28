param([string]$ApiHost="127.0.0.1",[int]$ApiPort=7497,[int]$ClientId=3021,[int]$Timeout=10)
$ErrorActionPreference="Stop"
$Py = ".\.venv\Scripts\python.exe"
$code = "from ib_insync import IB;import sys;h=sys.argv[1];p=int(sys.argv[2]);cid=int(sys.argv[3]);t=int(sys.argv[4]);ib=IB();" +
        "try:\n ok=ib.connect(h,p,clientId=cid,timeout=t);print(f'{h}:{p} connected={bool(ok)}');" +
        " print('serverTime', ib.serverTime()) if ok else None\nfinally:\n  [ib.disconnect() for _ in [0]]"
& $Py -c $code $ApiHost $ApiPort $ClientId $Timeout
