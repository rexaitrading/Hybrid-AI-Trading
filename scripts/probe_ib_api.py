from ib_insync import *
import os, sys
host = os.getenv("IB_HOST", "127.0.0.1")
port = int(os.getenv("IB_PORT", "4003"))
cid  = int(os.getenv("IB_CLIENT_ID", "3021"))
util.logToConsole(True)
ib = IB()
try:
    print(f"Probing IB API at {host}:{port} (clientId={cid}) ...")
    ok = ib.connect(host, port, clientId=cid, timeout=30)
    print("Connected:", bool(ok))
    if not ok: sys.exit(2)
    print("serverTime:", ib.reqCurrentTime())
    print("accounts:", ib.managedAccounts())
    print("clientVersion:", ib.clientVersion(), "serverVersion:", ib.serverVersion())
    sys.exit(0)
finally:
    ib.disconnect()