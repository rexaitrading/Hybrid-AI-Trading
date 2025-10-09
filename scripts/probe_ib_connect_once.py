import os
import sys

from ib_insync import IB

host = os.getenv("IB_HOST", "127.0.0.1")
port = int(os.getenv("IB_PORT", "4002"))
cid = int(os.getenv("IB_CLIENT_ID", "901"))

ib = IB()
try:
    ib.connect(host, port, clientId=cid, timeout=15)
    print("isConnected:", ib.isConnected())
    print("serverVersion:", ib.client.serverVersion())
    print("twsConnectionTime:", ib.client.twsConnectionTime())
    print("currentTime:", ib.reqCurrentTime())
    # Ask for next valid order id
    ib.client.reqIds(1)
    ib.sleep(0.5)
    print("nextValidId:", getattr(ib.client, "orderId", None))
    sys.exit(0)
except Exception as e:
    print("connect_error:", repr(e))
    sys.exit(2)
finally:
    if ib.isConnected():
        ib.disconnect()
