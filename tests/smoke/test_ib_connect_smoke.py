import os
from ib_insync import IB

HOST = os.environ.get("IB_HOST", "::1")
PORT = int(os.environ.get("IB_PORT", "7497"))
CID  = int(os.environ.get("IB_CLIENT_ID", "3021"))

def test_ib_connect_smoke_strict():
    ib = IB()
    ok = ib.connect(HOST, PORT, clientId=CID, timeout=8)
    assert ok and ib.isConnected()
    _ = ib.reqCurrentTime()
    ib.disconnect()